from __future__ import annotations

import json
from typing import Callable, TypeVar
from urllib import error
from uuid import UUID

from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.timer import Timer
from textual.widgets import Button, Input, ListView, Static

from mahkrabdtn.client import RelayClientError, RelayNodeClient
from mahkrabdtn.client.store.aliases import NodeAliasBook
from mahkrabdtn.interface.tui.models import ConversationMessage
from mahkrabdtn.interface.tui.widgets import AliasListItem, MessageLog
from mahkrabdtn.protocol.packet import MessagePacket


ReturnType = TypeVar("ReturnType")
MESSENGER_ERRORS = (
    OSError,
    RelayClientError,
    ValueError,
    TypeError,
    error.URLError,
    json.JSONDecodeError,
)
ALIAS_ERRORS = (KeyError, *MESSENGER_ERRORS)


class MessengerApp(App[None]):
    TITLE = "MahkrabDTN"
    SUB_TITLE = "messenger"
    CSS_PATH = "messenger.tcss"
    ENABLE_COMMAND_PALETTE = False
    COMMANDS = set()
    BINDINGS = [
        Binding("ctrl+c", "quit", "Quit", show=False),
        Binding("ctrl+q", "quit", "Quit", show=False),
        Binding("ctrl+r", "register", "Register", show=False),
        Binding("ctrl+n", "focus_recipient", "Recipient", show=False),
        Binding("ctrl+m", "focus_message", "Message", show=False),
        Binding("ctrl+b", "toggle_sidebar", "Aliases", show=False),
    ]

    def __init__(
        self,
        client: RelayNodeClient,
        aliases: NodeAliasBook,
        pollTimeout_ms: int = 4000,
        pollWait_ms: int = 1000,
        autoRegister: bool = True,
        autoAck: bool = True,
        autoPoll: bool = True,
    ) -> None:

        super().__init__()
        self.client = client
        self.aliases = aliases
        self.pollTimeout_ms = pollTimeout_ms
        self.pollWait_ms = pollWait_ms
        self.autoRegister = autoRegister
        self.autoAck = autoAck
        self.autoPoll = autoPoll
        self.pollTimer: Timer | None = None
        self.pollInProgress = False
        self.sidebarVisible = False

    def compose(self) -> ComposeResult:
        with Horizontal(id="layout"):
            with Vertical(id="sidebar"):
                yield Static("Node", classes="section-title")
                yield Static(id="identity")
                yield Static(id="status")
                yield Button("Register", id="registerButton", variant="primary")
                yield Static("Aliases", classes="section-title")
                yield ListView(id="aliasList")
                yield Input(placeholder="Alias", id="aliasInput")
                yield Input(placeholder="Node UUID", id="aliasNodeInput")
                with Horizontal(id="aliasButtons"):
                    yield Button("Save", id="saveAliasButton", variant="success")
                    yield Button("Remove", id="removeAliasButton")
            with Vertical(id="main"):
                yield MessageLog(
                    id="messages",
                    wrap=True,
                    highlight=False,
                    markup=False,
                    max_lines=500,
                )
                with Horizontal(id="composer"):
                    yield Input(placeholder="Recipient alias or node UUID", id="recipientInput")
                    yield Input(placeholder="Message", id="messageInput")

    async def on_mount(self) -> None:
        self.apply_sidebar_visibility()
        self.update_identity()
        self.set_status("Starting")
        await self.refresh_aliases()
        self.write_system("Ready")
        self.configure_inputs()
        self.query_one("#recipientInput", Input).focus()

        if self.autoRegister:
            self.register_node()
            return

        self.start_polling()

    def action_register(self) -> None:
        self.register_node()

    def action_focus_recipient(self) -> None:
        self.query_one("#recipientInput", Input).focus()

    def action_focus_message(self) -> None:
        self.query_one("#messageInput", Input).focus()

    def action_toggle_sidebar(self) -> None:
        self.sidebarVisible = not self.sidebarVisible
        self.apply_sidebar_visibility()

    def apply_sidebar_visibility(self) -> None:
        sidebar = self.query_one("#sidebar", Vertical)
        main = self.query_one("#main", Vertical)

        sidebar.set_class(not self.sidebarVisible, "hidden")
        main.set_class(not self.sidebarVisible, "wide")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        match event.button.id:
            case "registerButton":
                self.register_node()
            case "saveAliasButton":
                self.run_worker(self.save_alias_from_form(), group="ui")
            case "removeAliasButton":
                self.run_worker(self.remove_alias_from_form(), group="ui")

    def on_input_submitted(self, event: Input.Submitted) -> None:
        match event.input.id:
            case "recipientInput":
                self.query_one("#messageInput", Input).focus()
            case "messageInput":
                self.send_current_message()
            case "aliasInput":
                self.query_one("#aliasNodeInput", Input).focus()
            case "aliasNodeInput":
                self.run_worker(self.save_alias_from_form(), group="ui")

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        if not isinstance(event.item, AliasListItem): return

        alias = event.item.alias
        self.query_one("#recipientInput", Input).value = alias.name
        self.query_one("#aliasInput", Input).value = alias.name
        self.query_one("#aliasNodeInput", Input).value = str(alias.nodeID)
        self.query_one("#messageInput", Input).focus()

    async def save_alias_from_form(self) -> None:
        aliasInput = self.query_one("#aliasInput", Input)
        nodeInput = self.query_one("#aliasNodeInput", Input)

        try:
            alias = self.aliases.set_alias(aliasInput.value, nodeInput.value)
        except MESSENGER_ERRORS as caughtError:
            self.report_error(f"Could not save alias: {caughtError}")
            return

        await self.refresh_aliases()
        self.query_one("#recipientInput", Input).value = alias.name
        self.write_system(f"Alias saved: {alias.name}")

    async def remove_alias_from_form(self) -> None:
        aliasInput = self.query_one("#aliasInput", Input)

        try:
            self.aliases.remove_alias(aliasInput.value)
        except ALIAS_ERRORS as caughtError:
            self.report_error(f"Could not remove alias: {caughtError}")
            return

        aliasInput.value = ""
        self.query_one("#aliasNodeInput", Input).value = ""
        await self.refresh_aliases()
        self.write_system("Alias removed")

    async def refresh_aliases(self) -> None:
        aliasList = self.query_one("#aliasList", ListView)
        await aliasList.clear()

        for alias in self.aliases.aliases:
            await aliasList.append(AliasListItem(alias))

    def send_current_message(self) -> None:
        recipientInput = self.query_one("#recipientInput", Input)
        messageInput = self.query_one("#messageInput", Input)
        recipientText = recipientInput.value.strip()
        messageText = messageInput.value.strip()

        if not recipientText:
            self.report_error("Recipient is required")
            recipientInput.focus()
            return

        if not messageText:
            self.report_error("Message is required")
            messageInput.focus()
            return

        try:
            recipientID = self.aliases.resolve_node(recipientText)
        except MESSENGER_ERRORS as caughtError:
            self.report_error(f"Unknown recipient: {caughtError}")
            recipientInput.focus()
            return

        messageInput.value = ""
        self.set_status(f"Sending to {self.aliases.display_name(recipientID)}")
        self.send_message(recipientID, messageText)

    def start_polling(self) -> None:
        if not self.autoPoll or self.pollTimer is not None: return

        interval = max(self.pollWait_ms / 1000, 0.25)
        self.pollTimer = self.set_interval(interval, self.queue_poll, name="poll")
        self.queue_poll()

    def queue_poll(self) -> None:
        if self.pollInProgress: return

        self.pollInProgress = True
        self.set_status("Listening")
        self.poll_relay()

    def configure_inputs(self) -> None:
        for inputWidget in self.query(Input):
            inputWidget.cursor_blink = False

    @work(thread=True, group="register", exclusive=True, exit_on_error=False)
    def register_node(self) -> None:
        try:
            registration = self.client.register()
        except MESSENGER_ERRORS as caughtError:
            self.call_ui(self.handle_registration_error, str(caughtError))
            return

        self.call_ui(self.handle_registration_success, str(registration.nodeID))

    @work(thread=True, group="send", exit_on_error=False)
    def send_message(self, recipientID: UUID, payload: str) -> None:
        try:
            receipt = self.client.send_message(
                recipientID=recipientID,
                payload=payload,
            )
        except MESSENGER_ERRORS as caughtError:
            self.call_ui(self.handle_send_error, str(caughtError))
            return

        state = getattr(receipt.state, "value", str(receipt.state))
        self.call_ui(
            self.handle_send_success,
            recipientID,
            payload,
            str(receipt.messageID),
            state,
        )

    @work(thread=True, group="poll", exclusive=True, exit_on_error=False)
    def poll_relay(self) -> None:
        try:
            response = self.client.poll_messages(timeout_ms=self.pollTimeout_ms)
            ackErrors = self.acknowledge_messages(response.messages)
        except MESSENGER_ERRORS as caughtError:
            self.call_ui(self.handle_poll_error, str(caughtError))
            return
        finally:
            self.call_ui(self.finish_poll)

        self.call_ui(self.handle_poll_response, response.messages, ackErrors)

    def acknowledge_messages(self, messages: list[MessagePacket]) -> list[str]:
        if not self.autoAck: return []

        ackErrors: list[str] = []

        for message in messages:
            try:
                self.client.acknowledge_message(message.messageID)
            except MESSENGER_ERRORS as caughtError:
                ackErrors.append(f"{message.messageID}: {caughtError}")

        return ackErrors

    def handle_registration_success(self, nodeID: str) -> None:
        self.set_status("Registered")
        self.write_system(f"Registered node {nodeID}")
        self.start_polling()

    def handle_registration_error(self, message: str) -> None:
        self.report_error(f"Registration failed: {message}")

    def handle_send_success(
        self,
        recipientID: UUID,
        payload: str,
        messageID: str,
        state: str,
    ) -> None:

        self.set_status("Sent")
        self.write_conversation_message(
            ConversationMessage(
                direction="outbound",
                peerID=recipientID,
                messageID=messageID,
                payload=payload,
                state=state,
            )
        )
        self.query_one("#messageInput", Input).focus()

    def handle_send_error(self, message: str) -> None:
        self.report_error(f"Send failed: {message}")
        self.query_one("#messageInput", Input).focus()

    def handle_poll_response(
        self,
        messages: list[MessagePacket],
        ackErrors: list[str],
    ) -> None:

        for message in messages:
            self.write_conversation_message(
                ConversationMessage(
                    direction="inbound",
                    peerID=message.senderID,
                    messageID=message.messageID,
                    payload=message.payload,
                    created=message.created,
                    state="acknowledged" if self.autoAck else None,
                )
            )

        for ackError in ackErrors:
            self.report_error(f"Acknowledgement failed: {ackError}")

        if messages:
            self.set_status(f"Received {len(messages)}")
        else:
            self.set_status("Listening")

    def handle_poll_error(self, message: str) -> None:
        self.report_error(f"Poll failed: {message}")

    def finish_poll(self) -> None:
        self.pollInProgress = False

    def update_identity(self) -> None:
        aliasPath = str(self.aliases.path) if self.aliases.path is not None else "memory"
        self.query_one("#identity", Static).update(
            f"nodeID: {self.client.nodeID}\n"
            f"relay: {self.client.baseURL}\n"
            f"aliases: {aliasPath}"
        )

    def write_conversation_message(self, message: ConversationMessage) -> None:
        self.query_one("#messages", MessageLog).write_message(message, self.aliases)

    def write_system(self, message: str) -> None:
        self.write_conversation_message(
            ConversationMessage(direction="system", payload=message)
        )

    def report_error(self, message: str) -> None:
        self.set_status(message)
        self.write_system(message)

    def set_status(self, message: str) -> None:
        self.query_one("#status", Static).update(f"status: {message}")

    def call_ui(
        self,
        callback: Callable[..., ReturnType],
        *args: object,
    ) -> ReturnType | None:

        try:
            return self.call_from_thread(callback, *args)
        except RuntimeError:
            return None
