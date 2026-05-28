from __future__ import annotations

from rich.text import Text
from textual.widgets import Label, ListItem, RichLog

from mahkrabdtn.client.store.aliases import NodeAlias, NodeAliasBook
from mahkrabdtn.interface.tui.models import ConversationMessage


TIME_STYLE = "#777777"
PEER_STYLE = "#B10F5D"
MESSAGE_STYLE = "#A89FA7"
STATE_STYLE = "#322F32"
SYSTEM_STYLE = "#4E1D4C"

    
class AliasListItem(ListItem):
    def __init__(self, alias: NodeAlias) -> None:
        self.alias = alias
        label = Label(f"{alias.name}\n{alias.nodeID}", classes="alias-row")
        super().__init__(label)


class MessageLog(RichLog):
    def write_message(
        self,
        message: ConversationMessage,
        aliases: NodeAliasBook,
    ) -> None:

        if message.direction == "system":
            self.write(build_system_text(message), scroll_end=True)
            return

        name = aliases.display_name(message.peerID) if message.peerID is not None else "unknown"
        timeText = message.created.strftime("%H:%M:%S")
        directionText = "From" if message.direction == "inbound" else "To"

        text = Text.assemble(
            (timeText, TIME_STYLE),
            (f" {directionText} {name}", PEER_STYLE),
            ("\n", ""),
            (message.payload, MESSAGE_STYLE),
        )

        if message.state:
            text.append("\n")
            text.append(message.state, style=STATE_STYLE)

        self.write(text, scroll_end=True)


def build_system_text(message: ConversationMessage) -> Text:
    timeText = message.created.strftime("%H:%M:%S")
    return Text.assemble(
        (f"{timeText} ", TIME_STYLE),
        (message.payload, SYSTEM_STYLE),
    )
