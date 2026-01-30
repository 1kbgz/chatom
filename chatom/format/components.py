"""Interactive components for chatom.

This module provides interactive UI components like buttons, select menus,
and forms that can be rendered to platform-specific formats.

Supported platforms:
- Slack: Block Kit (buttons, select menus, modals)
- Discord: Components (buttons, select menus)
- Symphony: Symphony Elements (buttons, forms)
"""

from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import Field

from chatom.base import BaseModel

from .variant import FORMAT, Format

__all__ = (
    "ButtonStyle",
    "Button",
    "SelectOption",
    "SelectMenu",
    "ActionRow",
    "TextInput",
    "TextInputStyle",
    "Modal",
    "ComponentContainer",
)


class ButtonStyle(str, Enum):
    """Button visual styles."""

    PRIMARY = "primary"
    """Primary action button (usually colored)."""

    SECONDARY = "secondary"
    """Secondary action button (neutral)."""

    SUCCESS = "success"
    """Success/positive action (green)."""

    DANGER = "danger"
    """Destructive/negative action (red)."""

    LINK = "link"
    """Link button (opens URL)."""


class Button(BaseModel):
    """An interactive button component.

    Buttons can trigger actions or open URLs. They have a label,
    style, and either an action_id (for callbacks) or url (for links).

    Attributes:
        label: The button text.
        action_id: Unique identifier for this button action (for callbacks).
        style: Visual style of the button.
        url: URL to open (for link buttons).
        disabled: Whether the button is disabled.
        emoji: Optional emoji to display with the label.
        value: Optional value sent with the callback.
    """

    label: str = Field(
        description="Button text label.",
    )
    action_id: str = Field(
        default="",
        description="Unique identifier for button action (used in callbacks).",
    )
    style: ButtonStyle = Field(
        default=ButtonStyle.PRIMARY,
        description="Visual style of the button.",
    )
    url: Optional[str] = Field(
        default=None,
        description="URL to open (for link buttons).",
    )
    disabled: bool = Field(
        default=False,
        description="Whether the button is disabled.",
    )
    emoji: Optional[str] = Field(
        default=None,
        description="Emoji to display with the label.",
    )
    value: Optional[str] = Field(
        default=None,
        description="Value sent with the callback.",
    )

    def render(self, format: FORMAT = Format.MARKDOWN) -> Dict[str, Any]:
        """Render the button to platform-specific format.

        Args:
            format: The output format.

        Returns:
            Dict representation for the platform's API.
        """
        if format == Format.SLACK_MARKDOWN:
            return self._render_slack()
        elif format == Format.DISCORD_MARKDOWN:
            return self._render_discord()
        elif format == Format.SYMPHONY_MESSAGEML:
            return self._render_symphony()
        else:
            # Return generic dict for other formats
            return self._render_generic()

    def _render_slack(self) -> Dict[str, Any]:
        """Render for Slack Block Kit."""
        button: Dict[str, Any] = {
            "type": "button",
            "text": {
                "type": "plain_text",
                "text": self.label,
                "emoji": True,
            },
            "action_id": self.action_id or f"button_{id(self)}",
        }

        if self.url:
            button["url"] = self.url

        if self.value:
            button["value"] = self.value

        # Map styles to Slack
        if self.style == ButtonStyle.PRIMARY:
            button["style"] = "primary"
        elif self.style == ButtonStyle.DANGER:
            button["style"] = "danger"
        # Slack doesn't have success/secondary, they're default

        return button

    def _render_discord(self) -> Dict[str, Any]:
        """Render for Discord Components."""
        # Discord button styles: 1=Primary, 2=Secondary, 3=Success, 4=Danger, 5=Link
        style_map = {
            ButtonStyle.PRIMARY: 1,
            ButtonStyle.SECONDARY: 2,
            ButtonStyle.SUCCESS: 3,
            ButtonStyle.DANGER: 4,
            ButtonStyle.LINK: 5,
        }

        button: Dict[str, Any] = {
            "type": 2,  # Button component type
            "label": self.label,
            "style": style_map.get(self.style, 1),
            "disabled": self.disabled,
        }

        if self.url and self.style == ButtonStyle.LINK:
            button["url"] = self.url
        else:
            button["custom_id"] = self.action_id or f"button_{id(self)}"

        if self.emoji:
            button["emoji"] = {"name": self.emoji}

        return button

    def _render_symphony(self) -> str:
        """Render for Symphony MessageML."""
        # Symphony uses <button> tags in MessageML
        name = self.action_id or f"button_{id(self)}"
        style_class = f'class="{self.style.value}"' if self.style != ButtonStyle.PRIMARY else ""
        return f'<button name="{name}" {style_class}>{self.label}</button>'

    def _render_generic(self) -> Dict[str, Any]:
        """Render generic dict representation."""
        return {
            "type": "button",
            "label": self.label,
            "action_id": self.action_id,
            "style": self.style.value,
            "url": self.url,
            "disabled": self.disabled,
        }


class SelectOption(BaseModel):
    """An option in a select menu.

    Attributes:
        label: Display text for the option.
        value: Value sent when option is selected.
        description: Optional description text.
        emoji: Optional emoji to display.
        default: Whether this is the default selection.
    """

    label: str = Field(description="Display text for the option.")
    value: str = Field(description="Value sent when option is selected.")
    description: Optional[str] = Field(
        default=None,
        description="Optional description text.",
    )
    emoji: Optional[str] = Field(
        default=None,
        description="Optional emoji to display.",
    )
    default: bool = Field(
        default=False,
        description="Whether this is the default selection.",
    )


class SelectMenu(BaseModel):
    """A dropdown select menu component.

    Attributes:
        action_id: Unique identifier for this select action.
        placeholder: Placeholder text when no option is selected.
        options: List of selectable options.
        min_values: Minimum number of selections required.
        max_values: Maximum number of selections allowed.
        disabled: Whether the select is disabled.
    """

    action_id: str = Field(
        description="Unique identifier for select action.",
    )
    placeholder: str = Field(
        default="Select an option",
        description="Placeholder text.",
    )
    options: List[SelectOption] = Field(
        default_factory=list,
        description="Selectable options.",
    )
    min_values: int = Field(
        default=1,
        description="Minimum selections required.",
    )
    max_values: int = Field(
        default=1,
        description="Maximum selections allowed.",
    )
    disabled: bool = Field(
        default=False,
        description="Whether the select is disabled.",
    )

    def render(self, format: FORMAT = Format.MARKDOWN) -> Dict[str, Any]:
        """Render the select menu to platform-specific format."""
        if format == Format.SLACK_MARKDOWN:
            return self._render_slack()
        elif format == Format.DISCORD_MARKDOWN:
            return self._render_discord()
        elif format == Format.SYMPHONY_MESSAGEML:
            return self._render_symphony()
        else:
            return self._render_generic()

    def _render_slack(self) -> Dict[str, Any]:
        """Render for Slack Block Kit."""
        options = []
        for opt in self.options:
            option: Dict[str, Any] = {
                "text": {"type": "plain_text", "text": opt.label},
                "value": opt.value,
            }
            if opt.description:
                option["description"] = {"type": "plain_text", "text": opt.description}
            options.append(option)

        return {
            "type": "static_select",
            "action_id": self.action_id,
            "placeholder": {"type": "plain_text", "text": self.placeholder},
            "options": options,
        }

    def _render_discord(self) -> Dict[str, Any]:
        """Render for Discord Components."""
        options = []
        for opt in self.options:
            option: Dict[str, Any] = {
                "label": opt.label,
                "value": opt.value,
                "default": opt.default,
            }
            if opt.description:
                option["description"] = opt.description
            if opt.emoji:
                option["emoji"] = {"name": opt.emoji}
            options.append(option)

        return {
            "type": 3,  # Select menu component type
            "custom_id": self.action_id,
            "placeholder": self.placeholder,
            "options": options,
            "min_values": self.min_values,
            "max_values": self.max_values,
            "disabled": self.disabled,
        }

    def _render_symphony(self) -> str:
        """Render for Symphony MessageML."""
        options_ml = []
        for opt in self.options:
            selected = ' selected="true"' if opt.default else ""
            options_ml.append(f'<option value="{opt.value}"{selected}>{opt.label}</option>')

        options_str = "\n".join(options_ml)
        return f'<select name="{self.action_id}">\n{options_str}\n</select>'

    def _render_generic(self) -> Dict[str, Any]:
        """Render generic dict representation."""
        return {
            "type": "select",
            "action_id": self.action_id,
            "placeholder": self.placeholder,
            "options": [opt.model_dump() for opt in self.options],
        }


class ActionRow(BaseModel):
    """A row of interactive components.

    Components are laid out horizontally. Most platforms limit
    the number of components per row (e.g., Discord allows 5 buttons).

    Attributes:
        components: List of components in this row.
    """

    components: List[Union[Button, SelectMenu]] = Field(
        default_factory=list,
        description="Components in this row.",
    )

    def render(self, format: FORMAT = Format.MARKDOWN) -> Dict[str, Any]:
        """Render the action row to platform-specific format."""
        if format == Format.SLACK_MARKDOWN:
            return self._render_slack()
        elif format == Format.DISCORD_MARKDOWN:
            return self._render_discord()
        elif format == Format.SYMPHONY_MESSAGEML:
            return self._render_symphony()
        else:
            return self._render_generic()

    def _render_slack(self) -> Dict[str, Any]:
        """Render for Slack Block Kit."""
        elements = [comp.render(Format.SLACK_MARKDOWN) for comp in self.components]
        return {
            "type": "actions",
            "elements": elements,
        }

    def _render_discord(self) -> Dict[str, Any]:
        """Render for Discord Components."""
        components = [comp.render(Format.DISCORD_MARKDOWN) for comp in self.components]
        return {
            "type": 1,  # Action row component type
            "components": components,
        }

    def _render_symphony(self) -> str:
        """Render for Symphony MessageML."""
        parts = []
        for comp in self.components:
            if isinstance(comp, Button):
                parts.append(comp._render_symphony())
            elif isinstance(comp, SelectMenu):
                parts.append(comp._render_symphony())
        return " ".join(parts)

    def _render_generic(self) -> Dict[str, Any]:
        """Render generic dict representation."""
        return {
            "type": "action_row",
            "components": [comp.render(Format.MARKDOWN) for comp in self.components],
        }

    def add_button(
        self,
        label: str,
        action_id: str = "",
        style: ButtonStyle = ButtonStyle.PRIMARY,
        url: Optional[str] = None,
        value: Optional[str] = None,
    ) -> "ActionRow":
        """Add a button to the row.

        Args:
            label: Button text.
            action_id: Callback action identifier.
            style: Button style.
            url: URL for link buttons.
            value: Value sent with callback.

        Returns:
            Self for chaining.
        """
        self.components.append(
            Button(
                label=label,
                action_id=action_id,
                style=style,
                url=url,
                value=value,
            )
        )
        return self

    def add_select(
        self,
        action_id: str,
        options: List[SelectOption],
        placeholder: str = "Select an option",
    ) -> "ActionRow":
        """Add a select menu to the row.

        Args:
            action_id: Callback action identifier.
            options: List of options.
            placeholder: Placeholder text.

        Returns:
            Self for chaining.
        """
        self.components.append(
            SelectMenu(
                action_id=action_id,
                options=options,
                placeholder=placeholder,
            )
        )
        return self


class TextInputStyle(str, Enum):
    """Text input styles for modals."""

    SHORT = "short"
    """Single-line input."""

    PARAGRAPH = "paragraph"
    """Multi-line input."""


class TextInput(BaseModel):
    """A text input field for modals/forms.

    Attributes:
        action_id: Unique identifier for this input.
        label: Label displayed above the input.
        placeholder: Placeholder text.
        style: Input style (short or paragraph).
        min_length: Minimum input length.
        max_length: Maximum input length.
        required: Whether input is required.
        default_value: Default value.
    """

    action_id: str = Field(description="Unique identifier for this input.")
    label: str = Field(description="Label displayed above the input.")
    placeholder: str = Field(
        default="",
        description="Placeholder text.",
    )
    style: TextInputStyle = Field(
        default=TextInputStyle.SHORT,
        description="Input style.",
    )
    min_length: Optional[int] = Field(
        default=None,
        description="Minimum input length.",
    )
    max_length: Optional[int] = Field(
        default=None,
        description="Maximum input length.",
    )
    required: bool = Field(
        default=True,
        description="Whether input is required.",
    )
    default_value: str = Field(
        default="",
        description="Default value.",
    )

    def render(self, format: FORMAT = Format.MARKDOWN) -> Dict[str, Any]:
        """Render the text input to platform-specific format."""
        if format == Format.SLACK_MARKDOWN:
            return self._render_slack()
        elif format == Format.DISCORD_MARKDOWN:
            return self._render_discord()
        elif format == Format.SYMPHONY_MESSAGEML:
            return self._render_symphony()
        else:
            return self._render_generic()

    def _render_slack(self) -> Dict[str, Any]:
        """Render for Slack Block Kit (modal input)."""
        element: Dict[str, Any] = {
            "type": "plain_text_input",
            "action_id": self.action_id,
            "multiline": self.style == TextInputStyle.PARAGRAPH,
        }
        if self.placeholder:
            element["placeholder"] = {"type": "plain_text", "text": self.placeholder}
        if self.min_length:
            element["min_length"] = self.min_length
        if self.max_length:
            element["max_length"] = self.max_length
        if self.default_value:
            element["initial_value"] = self.default_value

        return {
            "type": "input",
            "label": {"type": "plain_text", "text": self.label},
            "element": element,
            "optional": not self.required,
        }

    def _render_discord(self) -> Dict[str, Any]:
        """Render for Discord Components (modal input)."""
        style = 1 if self.style == TextInputStyle.SHORT else 2

        component: Dict[str, Any] = {
            "type": 4,  # Text input component type
            "custom_id": self.action_id,
            "style": style,
            "label": self.label,
            "required": self.required,
        }
        if self.placeholder:
            component["placeholder"] = self.placeholder
        if self.min_length:
            component["min_length"] = self.min_length
        if self.max_length:
            component["max_length"] = self.max_length
        if self.default_value:
            component["value"] = self.default_value

        return {
            "type": 1,  # Action row wrapper
            "components": [component],
        }

    def _render_symphony(self) -> str:
        """Render for Symphony MessageML."""
        input_type = "textarea" if self.style == TextInputStyle.PARAGRAPH else "text-field"
        required = ' required="true"' if self.required else ""
        placeholder = f' placeholder="{self.placeholder}"' if self.placeholder else ""
        return f'<{input_type} name="{self.action_id}"{required}{placeholder}>{self.default_value}</{input_type}>'

    def _render_generic(self) -> Dict[str, Any]:
        """Render generic dict representation."""
        return {
            "type": "text_input",
            "action_id": self.action_id,
            "label": self.label,
            "style": self.style.value,
            "required": self.required,
        }


class Modal(BaseModel):
    """A modal dialog with form inputs.

    Modals are opened in response to interactions and contain
    form elements for user input.

    Attributes:
        callback_id: Unique identifier for form submission.
        title: Modal title.
        submit_label: Submit button text.
        close_label: Close/cancel button text.
        inputs: List of input elements.
    """

    callback_id: str = Field(description="Unique identifier for form submission.")
    title: str = Field(description="Modal title.")
    submit_label: str = Field(
        default="Submit",
        description="Submit button text.",
    )
    close_label: str = Field(
        default="Cancel",
        description="Close button text.",
    )
    inputs: List[TextInput] = Field(
        default_factory=list,
        description="Form input elements.",
    )

    def render(self, format: FORMAT = Format.MARKDOWN) -> Dict[str, Any]:
        """Render the modal to platform-specific format."""
        if format == Format.SLACK_MARKDOWN:
            return self._render_slack()
        elif format == Format.DISCORD_MARKDOWN:
            return self._render_discord()
        elif format == Format.SYMPHONY_MESSAGEML:
            return self._render_symphony()
        else:
            return self._render_generic()

    def _render_slack(self) -> Dict[str, Any]:
        """Render for Slack modal view."""
        blocks = [inp.render(Format.SLACK_MARKDOWN) for inp in self.inputs]

        return {
            "type": "modal",
            "callback_id": self.callback_id,
            "title": {"type": "plain_text", "text": self.title},
            "submit": {"type": "plain_text", "text": self.submit_label},
            "close": {"type": "plain_text", "text": self.close_label},
            "blocks": blocks,
        }

    def _render_discord(self) -> Dict[str, Any]:
        """Render for Discord modal."""
        components = [inp.render(Format.DISCORD_MARKDOWN) for inp in self.inputs]

        return {
            "type": 9,  # Modal response type
            "custom_id": self.callback_id,
            "title": self.title,
            "components": components,
        }

    def _render_symphony(self) -> str:
        """Render for Symphony form."""
        inputs_ml = [inp._render_symphony() for inp in self.inputs]
        inputs_str = "\n".join(inputs_ml)
        return f"""<form id="{self.callback_id}">
<h3>{self.title}</h3>
{inputs_str}
<button name="submit" type="action">{self.submit_label}</button>
</form>"""

    def _render_generic(self) -> Dict[str, Any]:
        """Render generic dict representation."""
        return {
            "type": "modal",
            "callback_id": self.callback_id,
            "title": self.title,
            "inputs": [inp.render(Format.MARKDOWN) for inp in self.inputs],
        }

    def add_text_input(
        self,
        action_id: str,
        label: str,
        placeholder: str = "",
        style: TextInputStyle = TextInputStyle.SHORT,
        required: bool = True,
    ) -> "Modal":
        """Add a text input to the modal.

        Args:
            action_id: Unique identifier.
            label: Input label.
            placeholder: Placeholder text.
            style: Short or paragraph.
            required: Whether required.

        Returns:
            Self for chaining.
        """
        self.inputs.append(
            TextInput(
                action_id=action_id,
                label=label,
                placeholder=placeholder,
                style=style,
                required=required,
            )
        )
        return self


class ComponentContainer(BaseModel):
    """Container for interactive components attached to a message.

    This wraps action rows and can be attached to a FormattedMessage.

    Attributes:
        rows: List of action rows.
    """

    rows: List[ActionRow] = Field(
        default_factory=list,
        description="Action rows containing components.",
    )

    def render(self, format: FORMAT = Format.MARKDOWN) -> List[Dict[str, Any]]:
        """Render all rows to platform-specific format."""
        if format == Format.SYMPHONY_MESSAGEML:
            # Symphony uses inline MessageML
            parts = [row._render_symphony() for row in self.rows]
            return [{"messageml": "\n".join(parts)}]
        else:
            return [row.render(format) for row in self.rows]

    def add_row(self) -> ActionRow:
        """Add a new action row and return it.

        Returns:
            The new action row for adding components.
        """
        row = ActionRow()
        self.rows.append(row)
        return row

    def add_button(
        self,
        label: str,
        action_id: str = "",
        style: ButtonStyle = ButtonStyle.PRIMARY,
        url: Optional[str] = None,
    ) -> "ComponentContainer":
        """Add a button to the last row (creates row if needed).

        Args:
            label: Button text.
            action_id: Callback action identifier.
            style: Button style.
            url: URL for link buttons.

        Returns:
            Self for chaining.
        """
        if not self.rows:
            self.add_row()

        self.rows[-1].add_button(label, action_id, style, url)
        return self

    def add_select(
        self,
        action_id: str,
        options: List[SelectOption],
        placeholder: str = "Select an option",
    ) -> "ComponentContainer":
        """Add a select menu (creates new row for it).

        Args:
            action_id: Callback action identifier.
            options: List of options.
            placeholder: Placeholder text.

        Returns:
            Self for chaining.
        """
        # Select menus typically need their own row
        row = self.add_row()
        row.add_select(action_id, options, placeholder)
        return self
