# simple action: sets slot transfer_to -> agent_support
from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet

class ActionTransferTo(Action):
    def name(self) -> Text:
        return "action_transfer_to"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        dispatcher.utter_message(text="Сейчас я вас перенаправлю в техподдержку.")
        # set slot "transfer_to" with target agent name:
        return [SlotSet("transfer_to", "agent_support")]
