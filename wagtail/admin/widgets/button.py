from django.forms.utils import flatatt
from django.urls import reverse
from django.utils.functional import cached_property
from django.utils.http import urlencode

from wagtail import hooks
from wagtail.admin.ui.components import Component


class Button(Component):
    template_name = "wagtailadmin/shared/button.html"
    show = True
    label = ""
    icon_name = None
    url = None
    attrs = {}

    def __init__(
        self, label="", url=None, classname="", icon_name=None, attrs={}, priority=1000
    ):
        if label:
            self.label = label

        if url:
            self.url = url

        self.classname = classname

        if icon_name:
            self.icon_name = icon_name

        self.attrs = self.attrs.copy()
        self.attrs.update(attrs)

        # if a 'title' attribute has been passed, correct that to aria-label
        # as that's what will be picked up in renderings that don't use button.render
        # directly (e.g. _dropdown_items.html)
        if "title" in self.attrs and "aria-label" not in self.attrs:
            self.attrs["aria-label"] = self.attrs.pop("title")
        self.priority = priority

    def get_context_data(self, parent_context):
        return {"button": self}

    @property
    def base_attrs_string(self):
        # The set of attributes to be included on all renderings of
        # the button, as a string. Does not include the href or class
        # attributes (since the classnames intended for the button styling
        # should not be applied to dropdown items)
        return flatatt(self.attrs)

    @property
    def aria_label(self):
        return self.attrs.get("aria-label", "")

    def __repr__(self):
        return f"<Button: {self.label}>"

    def __lt__(self, other):
        if not isinstance(other, Button):
            return NotImplemented
        return (self.priority, self.label) < (other.priority, other.label)

    def __le__(self, other):
        if not isinstance(other, Button):
            return NotImplemented
        return (self.priority, self.label) <= (other.priority, other.label)

    def __gt__(self, other):
        if not isinstance(other, Button):
            return NotImplemented
        return (self.priority, self.label) > (other.priority, other.label)

    def __ge__(self, other):
        if not isinstance(other, Button):
            return NotImplemented
        return (self.priority, self.label) >= (other.priority, other.label)

    def __eq__(self, other):
        if not isinstance(other, Button):
            return NotImplemented
        return (
            self.label == other.label
            and self.url == other.url
            and self.classname == other.classname
            and self.attrs == other.attrs
            and self.priority == other.priority
        )


class HeaderButton(Button):
    """An icon-only button to be displayed after the breadcrumbs in the header."""

    def __init__(
        self,
        label="",
        url=None,
        classname="",
        icon_name=None,
        attrs={},
        icon_only=False,
        **kwargs,
    ):
        classname = f"{classname} w-header-button button".strip()
        attrs = attrs.copy()
        if icon_only:
            controller = f"{attrs.get('data-controller', '')} w-tooltip".strip()
            attrs["data-controller"] = controller
            attrs["data-w-tooltip-content-value"] = label
            attrs["aria-label"] = label
            label = ""

        super().__init__(
            label=label,
            url=url,
            classname=classname,
            icon_name=icon_name,
            attrs=attrs,
            **kwargs,
        )


# Base class for all listing buttons
# This is also used by SnippetListingButton defined in wagtail.snippets.widgets
class ListingButton(Button):
    def __init__(self, label="", url=None, classname="", **kwargs):
        classname = f"{classname} button button-small button-secondary".strip()
        super().__init__(label=label, url=url, classname=classname, **kwargs)


class PageListingButton(ListingButton):
    aria_label_format = None
    url_name = None

    def __init__(self, *args, page=None, next_url=None, attrs={}, user=None, **kwargs):
        self.page = page
        self.user = user
        self.next_url = next_url

        attrs = attrs.copy()
        if (
            self.page
            and self.aria_label_format is not None
            and "aria-label" not in attrs
        ):
            attrs["aria-label"] = self.aria_label_format % {
                "title": self.page.get_admin_display_title()
            }
        super().__init__(*args, attrs=attrs, **kwargs)

    @cached_property
    def url(self):
        if self.page and self.url_name is not None:
            url = reverse(self.url_name, args=[self.page.id])
            if self.next_url:
                url += "?" + urlencode({"next": self.next_url})
            return url

    @cached_property
    def page_perms(self):
        if self.page:
            return self.page.permissions_for_user(self.user)


class BaseDropdownMenuButton(Button):
    template_name = "wagtailadmin/pages/listing/_button_with_dropdown.html"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, url=None, **kwargs)

    @cached_property
    def dropdown_buttons(self):
        raise NotImplementedError

    def get_context_data(self, parent_context):
        return {
            "buttons": sorted(self.dropdown_buttons),
            "label": self.label,
            "title": self.aria_label,
            "toggle_classname": self.classname,
            "icon_name": self.icon_name,
        }


class ButtonWithDropdown(BaseDropdownMenuButton):
    def __init__(self, *args, **kwargs):
        self.dropdown_buttons = kwargs.pop("buttons", [])
        super().__init__(*args, **kwargs)


class ButtonWithDropdownFromHook(BaseDropdownMenuButton):
    def __init__(
        self,
        label,
        hook_name,
        page,
        user,
        next_url=None,
        **kwargs,
    ):
        self.hook_name = hook_name
        self.page = page
        self.user = user
        self.next_url = next_url

        super().__init__(label, **kwargs)

    @property
    def show(self):
        return bool(self.dropdown_buttons)

    @cached_property
    def dropdown_buttons(self):
        button_hooks = hooks.get_hooks(self.hook_name)

        buttons = []
        for hook in button_hooks:
            buttons.extend(hook(page=self.page, user=self.user, next_url=self.next_url))

        buttons = [b for b in buttons if b.show]
        return buttons
