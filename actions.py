# This files contains your custom actions which can be used to run
# custom Python code.
#
# See this guide on how to implement these action:
# https://rasa.com/docs/rasa/core/actions/#custom-actions/


# This is a simple example for a custom action which utters "Hello World!"

from typing import Any, Coroutine, Text, Dict, List
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet, FollowupAction, Restarted
from rasa.shared.core.events import Event
from typing import Text, List, Any, Dict
from rasa_sdk import Tracker, FormValidationAction
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.types import DomainDict
from itertools import islice

import re
import sqlite3

class ActionGetMenu(Action):
    def name(self) -> Text:
        return "action_get_menu"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        connection = sqlite3.connect('menu.db')
        cursor = connection.cursor()

        cursor.execute("SELECT name, price_small, price_medium, price_large, price_extra_large FROM menu")
        results = cursor.fetchall()

        if results:
            menu_text = "Here is our menu:\n\n"
            for row in results:
                menu_text += f"{row[0]} | Small: {row[1]:.2f}$ | Medium: {row[2]:.2f}$ | Large: {row[3]:.2f}$ | Extra Large: {row[4]:.2f}\n"
            menu_text += "\n\n Note that we have also different type of toppings and crusts that you can add. This would add to the order 1$ for each topping and from 1$ to 3$ for different crusts."
            dispatcher.utter_message(text=menu_text)
        else:
            dispatcher.utter_message(text="Sorry, the menu is currently unavailable.")

        connection.close()
        return []
    
class ActionGetCrustPrices(Action):
    def name(self) -> Text:
        return "action_get_crusts_price"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        connection = sqlite3.connect('menu.db')
        cursor = connection.cursor()
        pizza_crust = tracker.get_slot("pizza_crust")
        
        if pizza_crust is None:
            cursor.execute("SELECT type, price FROM crust")
            results = cursor.fetchall()

            if results:
                crust_menu_text = "Here is our crusts prices:\n\n"
                for row in results:
                    crust_menu_text += f"{row[0]} : {row[1]:.2f}$\n"
                dispatcher.utter_message(text=crust_menu_text)
            else:
                dispatcher.utter_message(text="Sorry, the crusts menu is currently unavailable.")
        else:
            query = "SELECT price FROM crust WHERE type LIKE ?"
            cursor.execute(query, (pizza_crust,))
            results = cursor.fetchall()

            if results:
                crust_menu_text = f"Here is our crusts price:{row[0]:.2f}$\n"
                dispatcher.utter_message(text=crust_menu_text)
            else:
                dispatcher.utter_message(text="Sorry, the crusts menu is currently unavailable.")
        
        connection.close()
        return []
    
class ActionGetPizzaIngredients(Action):
    def name(self) -> Text:
        return "action_get_pizza_ingredients"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        pizza_type = tracker.get_slot('pizza_type')

        if not pizza_type:
            dispatcher.utter_message(text="Please provide the pizza type.")
            return []

        connection = sqlite3.connect('menu.db')
        cursor = connection.cursor()
        query = '''
            SELECT i.ingredient
            FROM ingredients i
            JOIN pizza_ingredients pi ON i.id = pi.ingredient_id
            JOIN menu m ON pi.pizza_id = m.id
            WHERE m.name = ?
        '''
        cursor.execute(query, (pizza_type,))
        ingredients = cursor.fetchall()

        if ingredients:
            ingredient_text = f"Ingredients for {pizza_type}:\n\n"
            for ingredient in ingredients:
                ingredient_text += f"- {ingredient[0]}\n"
            dispatcher.utter_message(text=ingredient_text)
        else:
            dispatcher.utter_message(text=f"Sorry, I couldn't find the ingredients for the pizza named {pizza_type}.")

        connection.close()
        return []

class ActionGetAvailableToppings(Action):
    def name(self) -> Text:
        return "action_get_available_toppings"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        connection = sqlite3.connect('menu.db')
        cursor = connection.cursor()

        cursor.execute("SELECT ingredent FROM ingredients")
        results = cursor.fetchall()

        if results:
            toppings_text = "Here is our available toppings:\n\n"
            for row in results:
                toppings_text += f"{row[0]}\n"
            dispatcher.utter_message(text=toppings_text)
        else:
            dispatcher.utter_message(text="Sorry, the toppings are currently unavailable.")

        connection.close()
        return []

class ActionRestart(Action):
    def name(self) -> Text:
        return "action_restart"
    async def run(
        self, dispatcher, tracker: Tracker, domain: Dict[Text, Any]
    ):
        return [Restarted(), FollowupAction("action_wait")]
    
class ActionConfirmOrder(Action):
    def name(self):
        return 'action_confirm_order'
    async def run(self, dispatcher, tracker, domain):
        pizza_size = tracker.get_slot("pizza_size")
        pizza_type = tracker.get_slot("pizza_type")
        pizza_amount = tracker.get_slot("pizza_amount")
        pizza_crust = tracker.get_slot("pizza_crust")
        order_details = ""
        toppings = tracker.get_slot("pizza_toppings")
        if toppings is not None:
            toppings = ", ".join(toppings) if toppings is not None else ""
            toppings = toppings.rsplit(', ', 1)
            toppings = " and ".join(toppings)
            toppings = "with " + toppings
            order_details += f"{pizza_amount} {pizza_size} {pizza_crust} crust {pizza_type} {toppings}"
        else:
            order_details += f"{pizza_amount} {pizza_size} {pizza_crust} crust {pizza_type}"
        if tracker.get_slot("second_pizza_amount") is not None or tracker.get_slot("second_pizza_type") is not None or tracker.get_slot("second_pizza_size") is not None or tracker.get_slot("second_pizza_crust") is not None:
            dispatcher.utter_message(text="At the moment, the order is "+ order_details + ". Is everything correct?")
        else:
            dispatcher.utter_message(text="Your order is "+ order_details +". Is everything correct?")
        old_order = tracker.get_slot("current_order")
        current_order = (old_order + [order_details]) if old_order is not None else [order_details]
        return [SlotSet("current_order", current_order)]

class ActionTotalOrder(Action):
    def name(self):
        return 'action_total_order'
    async def run(self, dispatcher, tracker, domain):
        total_order = tracker.get_slot("total_order")
        total_price = tracker.get_slot("total_price")
        if total_order is None:
            dispatcher.utter_message(text="Sorry, there is an error. You have no open order.")
            return []
        else:
            total_order = ", and ".join(total_order)
            dispatcher.utter_message(text=f"Okay, great! Your total order is {total_order}. It will cost ${total_price}. Do you prefer take away or home delivery?")
            return [SlotSet("total_order", total_order)]

        
class ActionCancelCurrentOrder(Action):
    def name(self):
        return 'action_cancel_current_order'
    async def run(self, dispatcher, tracker, domain):
        current_order = tracker.get_slot("current_order")
        if current_order is None:
            dispatcher.utter_message(text="Sorry, there is an error. You have no open order.")
            return []
        else:
            if len(current_order) > 0:
                current_order.pop(-1)
                return [SlotSet("current_order", current_order if len(current_order) > 0 else None)]
            return [SlotSet("current_order", None)]
        
class ActionNewOrder(Action):
    def name(self) -> Text:
        return "action_new_order"
    async def run(self, dispatcher, tracker: Tracker, domain):
        second_pizza_type = tracker.get_slot("second_pizza_type")
        second_pizza_size = tracker.get_slot("second_pizza_size")
        second_pizza_amount = tracker.get_slot("second_pizza_amount")
        second_pizza_crust = tracker.get_slot("second_pizza_crust")

        next_pizza_type = None
        next_pizza_size = None
        next_pizza_amount = None
        next_pizza_crust = None
        events = []
        doForm = False
        if second_pizza_type is not None:
            next_pizza_type = second_pizza_type.pop(0)
            events += [SlotSet("pizza_type", next_pizza_type), SlotSet("second_pizza_type", second_pizza_type if len(second_pizza_type) > 0 else None)]
            doForm = True
        else:
            events += [SlotSet("pizza_type", None)]
        if second_pizza_size is not None:
            next_pizza_size = second_pizza_size.pop(0)
            events += [SlotSet("pizza_size", next_pizza_size), SlotSet("second_pizza_size", second_pizza_size if len(second_pizza_size) > 0 else None)]
            doForm = True
        else:
            events += [SlotSet("pizza_size", None)]
        if second_pizza_amount is not None:
            next_pizza_amount = second_pizza_amount.pop(0)
            events += [SlotSet("pizza_amount", next_pizza_amount), SlotSet("second_pizza_amount", second_pizza_amount if len(second_pizza_amount) > 0 else None)]
            doForm = True
        else:
            events += [SlotSet("pizza_amount", None)]
        if second_pizza_crust is not None:
            next_pizza_crust = second_pizza_crust.pop(0)
            events +=  [SlotSet("pizza_crust", next_pizza_crust), SlotSet("second_pizza_crust", second_pizza_crust if len(second_pizza_crust) > 0 else None)]
            doForm = True
        else:
            events += [SlotSet("pizza_crust", None)]
        if next_pizza_type is not None or next_pizza_size is not None or next_pizza_amount is not None or next_pizza_crust is not None:
            next_order= ""
            next_order += f"{next_pizza_amount} " if next_pizza_amount is not None else ""
            next_order += f"{next_pizza_size} " if next_pizza_size is not None else ""
            next_order += f"{next_pizza_crust} crust " if next_pizza_crust is not None else ""
            next_order += f"{next_pizza_type}" if next_pizza_type is not None else ""
            dispatcher.utter_message(text=f"Alright, let's go through the next {next_order} pizza.")
        return []
        
class ActionPizzaOrderAdd(Action):
    def name(self):
        return 'action_pizza_order_add'
    async def run(self, dispatcher, tracker, domain):
        current_order = tracker.get_slot("current_order")
        if current_order is None:
            dispatcher.utter_message(text="Sorry, there is an error. You have no open order.")
            return []
        total_order = tracker.get_slot("total_order")
        if total_order is None:
            total_order = []
        total_order.extend(tracker.get_slot("current_order"))

        type = tracker.get_slot('pizza_type')
        size = tracker.get_slot('pizza_size')
        amount = tracker.get_slot('pizza_amount')
        crust = tracker.get_slot('pizza_crust')
        toppings =  tracker.get_slot('pizza_toppings')
        
        price_column = f'price_{size}'
        n_toppings = len(toppings.split(','))
        
        try:
            connection = sqlite3.connect('menu.db')
            cursor = connection.cursor()
            query = 'SELECT ? FROM menu WHERE name==?'
            cursor.execute(query, (price_column, type))
            pizza_price = cursor.fetchall()
            
            query2 = 'SELECT price FROM menu WHERE type==?'
            cursor.execute(query2, (crust,))
            crusts_price = cursor.fetchall()
            
            connection.close()
        except sqlite3.Error as e:
            print(f"An error occurred: {e}")
            
        total_price = (pizza_price + crusts_price + n_toppings) * amount        
        dispatcher.utter_message(text=f"Your pizza(s) has been placed successfully! Your partial price is {total_price}$.")
        
        return [SlotSet("total_order", total_order), 
                SlotSet("total_price", total_price), 
                SlotSet("pizza_type", None),
                SlotSet("pizza_size", None),
                SlotSet("pizza_amount", None), 
                SlotSet("pizza_crust", None),  
                SlotSet("pizza_toppings", None), 
                SlotSet("current_order", None)
        ]

class ActionResetPizzaForm(Action):
    def name(self):
        return 'action_reset_pizza_form'
    async def run(self, dispatcher, tracker, domain):
        return[SlotSet("pizza_type", None),SlotSet("pizza_size", None),SlotSet("pizza_amount", None), SlotSet("pizza_crust", None), SlotSet("current_order", None)]

class ActionOrderNumber(Action):
    def name(self):
        return 'action_order_number'
    async def run(self, dispatcher, tracker, domain):
        name_person = tracker.get_slot("client_name")
        number_person = tracker.get_slot("client_phone_number")
        order_number =  str(name_person + "_" + number_person)
        print(order_number)
        return[SlotSet("order_number", order_number)]


class ValidatePizzaOrderForm(FormValidationAction):
    def __init__(self) -> None:
        super().__init__()
        self.warn_user = False
    def name(self) -> Text:
        return "validate_pizza_order_form"
    @staticmethod
    def get_menu() -> List[Text]:
        """Available pizzas from the database"""
        pizza_menu = []
        try:
            connection = sqlite3.connect('menu.db')
            cursor = connection.cursor()
            cursor.execute("SELECT name FROM menu")
            results = cursor.fetchall()
            pizza_menu = [row[0] for row in results]
            connection.close()
        except sqlite3.Error as e:
            print(f"An error occurred: {e}")

        return pizza_menu
    @staticmethod
    def get_toppings() -> List[Text]:
        """Available toppings from the database"""
        toppings = []
        try:
            connection = sqlite3.connect('menu.db')
            cursor = connection.cursor()
            cursor.execute("SELECT ingredent FROM ingredients")
            results = cursor.fetchall()
            toppings = [row[0] for row in results]
            connection.close()
        except sqlite3.Error as e:
            print(f"An error occurred: {e}")

        return toppings
    def reset_warn(self):
        self.warn_user = False
    def warn_user_one_at_time(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: DomainDict) -> None:
        if not self.warn_user:
            pizza_type = tracker.get_slot("pizza_type")
            pizza_size = tracker.get_slot("pizza_size")
            pizza_amount = tracker.get_slot("pizza_amount")
            pizza_crust = tracker.get_slot("pizza_crust")
            pizza_toppings = tracker.get_slot("pizza_toppings")
            second_pizza_type = tracker.get_slot("second_pizza_type")
            second_pizza_size = tracker.get_slot("second_pizza_size")
            second_pizza_amount = tracker.get_slot("second_pizza_amount")
            second_pizza_crust = tracker.get_slot("second_pizza_crust")
            second_pizza_toppings = tracker.get_slot("second_pizza_toppings")
            if second_pizza_type is not None or second_pizza_size is not None or second_pizza_amount is not None or second_pizza_crust is not None or second_pizza_toppings is not None:
                if second_pizza_type is not None and pizza_type is not None:
                    dispatcher.utter_message(text=f"Got it. For now, let’s stick to the {pizza_type} pizza.")
                elif second_pizza_size is not None and pizza_size is not None:
                    dispatcher.utter_message(text=f"Understood. Let's concentrate on the first {pizza_size} pizza.")
                elif second_pizza_amount is not None and pizza_amount is not None:
                    dispatcher.utter_message(text=f"Alright. We’ll focus on the first {pizza_amount} pizza for now.")
                elif second_pizza_crust is not None and pizza_crust is not None:
                    dispatcher.utter_message(text=f"Okay. We’ll handle the first {pizza_crust} pizza first.")
                elif pizza_toppings is not None and second_pizza_toppings is not None:
                    dispatcher.utter_message(text=f"Okay. We’ll handle the first {pizza_toppings} pizza first.")
                self.warn_user = True
            return True
        else:
            return False
    def validate_pizza_type(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> Dict[Text, Any]:
        if isinstance(slot_value, str):
            if slot_value.lower() in self.get_menu():
                self.warn_user_one_at_time(dispatcher, tracker, domain)
                return {"pizza_type": slot_value}
            else:
                return {"pizza_type": "Special " + slot_value.title() }
        elif isinstance(slot_value, list):
            if len(slot_value) > 0:
                concatenated_slot = ", ".join(slot_value)
                return {"pizza_type": concatenated_slot}
            else:
                return {"pizza_type": None}
    def validate_pizza_amount(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> Dict[Text, Any]:
        if isinstance(slot_value, str):
            if slot_value in ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12", "13", "14", "15", "16", "17", "18", "19", "20",
                        "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten",
                        "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen", "seventeen", "eighteen", "nineteen", "twenty"]:
                self.warn_user_one_at_time(dispatcher, tracker, domain)
                return {"pizza_amount": slot_value}
            else:
                dispatcher.utter_message(text="Please tell me a valid number (from 1 to 20).")
                return {"pizza_amount": None}
        elif isinstance(slot_value, list):
            if len(slot_value) > 0:
                concatenated_slot = ", ".join(slot_value)
                return {"pizza_amount": concatenated_slot}
            else:
                dispatcher.utter_message(text="Please tell me a valid number (from 1 to 20).")
                return {"pizza_amount": None}
    def validate_pizza_size(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> Dict[Text, Any]:
        if slot_value is None:
            dispatcher.utter_message(text="No size provided. Setting the default size to 'medium'.")
            return {"pizza_size": "medium"}
        
        if isinstance(slot_value, str):
            if slot_value.lower() in ["small", "medium", "large", "extra large"]:
                self.warn_user_one_at_time(dispatcher, tracker, domain)
                return {"pizza_size": slot_value}
            else:
                dispatcher.utter_message(text="Please tell me a valid size.")
                dispatcher.utter_message(response="utter_inform_pizza_size")
                return {"pizza_size": None}
        elif isinstance(slot_value, list):
            if len(slot_value) > 0:
                concatenated_slot = ", ".join(slot_value)
                return {"pizza_size": concatenated_slot}
            else:
                dispatcher.utter_message(text="Please tell me a valid size.")
                dispatcher.utter_message(response="utter_inform_pizza_size")
                return {"pizza_size": None}
    def validate_pizza_crust(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> Dict[Text, Any]:
        valid_crusts = ["thin", "thick", "stuffed", "gluten-free", "whole wheat", "flatbread", "cracker"]
        if slot_value is None:
            dispatcher.utter_message(text="No crust type provided. Setting the default crust to 'thin'.")
            return {"pizza_crust": "thin"}
        
        if isinstance(slot_value, str):
            if slot_value.lower() in valid_crusts:
                return {"pizza_crust": slot_value.lower()}
            else:
                dispatcher.utter_message(text="Please tell me a valid crust type.")
                dispatcher.utter_message(response="utter_inform_pizza_crust")
                return {"pizza_crust": None}
        
        elif isinstance(slot_value, list):
            if len(slot_value) > 0:
                concatenated_slot = ", ".join([s.lower() for s in slot_value])
                return {"pizza_crust": concatenated_slot}
            else:
                dispatcher.utter_message(text="Please tell me a valid crust type.")
                dispatcher.utter_message(response="utter_inform_pizza_crust")
                return {"pizza_crust": None}
    def validate_toppings(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> Dict[Text, Any]:
        """Validate the toppings slot, considering it as optional."""
        if slot_value is None:
            return {"toppings": []}

        if isinstance(slot_value, str):
            toppings_list = [topping.strip() for topping in slot_value.split(",") if topping.strip()]
        elif isinstance(slot_value, list):
            toppings_list = [topping.strip() for topping in slot_value if topping.strip()]
        else:
            dispatcher.utter_message(text="Please provide a valid list of toppings.")
            dispatcher.utter_message(response="action_get_available_toppings")
            return {"toppings": None}

        valid_toppings = self.get_toppings()
        invalid_toppings = [topping for topping in toppings_list if topping.lower() not in valid_toppings]

        if invalid_toppings:
            dispatcher.utter_message(
                text=f"The following toppings are not recognized: {', '.join(invalid_toppings)}. Please provide valid toppings."
            )
            dispatcher.utter_message(response="action_get_available_toppings")
            return {"toppings": None}
        return {"toppings": toppings_list}
    

class ActionTypeMapping(Action):
    def name(self) -> Text:
        return "action_type_mapping"
    async def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: DomainDict) -> Coroutine[Any, Any, List[Dict[Text, Any]]]:
        last_intent = tracker.get_intent_of_latest_message()
        if last_intent == "item_start_generic": 
            pizza_type = tracker.get_slot("pizza_type")
            ent_pizza_type = next(tracker.get_latest_entity_values("pizza_type"), None)
            if ent_pizza_type is None:
                return []
            else:
                if pizza_type is None:
                    return [SlotSet("pizza_type", ent_pizza_type)]
                else:
                    return [SlotSet("pizza_type", pizza_type)]
        return []
    
class ActionSizeMapping(Action):
    def name(self) -> Text:
        return "action_size_mapping"
    async def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: DomainDict) -> Coroutine[Any, Any, List[Dict[Text, Any]]]:
        last_intent = tracker.get_intent_of_latest_message()
        if last_intent == "item_start_generic": 
            pizza_size = tracker.get_slot("pizza_size")
            ent_pizza_size = next(tracker.get_latest_entity_values("pizza_size"), None)
            if ent_pizza_size is None:
                return []
            else:
                if pizza_size is None:
                    return [SlotSet("pizza_size", ent_pizza_size)]
                else:
                    return [SlotSet("pizza_size", pizza_size)]
        return []
    
class ActionAmountMapping(Action):
    def name(self) -> Text:
        return "action_amount_mapping"
    async def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: DomainDict) -> Coroutine[Any, Any, List[Dict[Text, Any]]]:
        last_intent = tracker.get_intent_of_latest_message()
        if last_intent == "item_start_generic": 
            pizza_amount = tracker.get_slot("pizza_amount")
            ent_pizza_amount = next(tracker.get_latest_entity_values("pizza_amount"), None)
            if ent_pizza_amount is None:
                return []
            else:
                if pizza_amount is None:
                    return [SlotSet("pizza_amount", ent_pizza_amount)]
                else:
                    return [SlotSet("pizza_amount", pizza_amount)]
        return []
    
class ActionCrustMapping(Action):
    def name(self) -> Text:
        return "action_crust_mapping"
    async def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: DomainDict) -> Coroutine[Any, Any, List[Dict[Text, Any]]]:
        last_intent = tracker.get_intent_of_latest_message()
        if last_intent == "item_start_generic": 
            pizza_crust = tracker.get_slot("pizza_crust")
            ent_pizza_crust = next(tracker.get_latest_entity_values("pizza_crust"), None)
            if ent_pizza_crust is None:
                return []
            else:
                if pizza_crust is None:
                    return [SlotSet("pizza_crust", ent_pizza_crust)]
                else:
                    return [SlotSet("pizza_crust", pizza_crust)]
        return []
 
class ActionAskPizzaAmount(Action):
    def name(self):
        return 'action_ask_pizza_amount'
    async def run(self, dispatcher, tracker, domain):
        last_intent = tracker.get_intent_of_latest_message()
        requested_slot = tracker.get_slot("requested_slot")
        if requested_slot == "pizza_amount" and last_intent not in ["request_pizza_crusts", "request_pizza_sizes", "request_pizza_types", "request_payment_methods", "stop", "verbose", "response_negative", "bot", "item_change", "item_change_request_without_entity"]:
            dispatcher.utter_message(response="utter_ask_pizza_amount_again")
            return []
        if last_intent == "item_start_generic":
            if requested_slot == "pizza_type" and tracker.get_slot("pizza_type") is not None:
                dispatcher.utter_message(response="utter_ask_pizza_amount_ack_type")
            elif requested_slot == "pizza_size" and tracker.get_slot("pizza_size") is not None:
                dispatcher.utter_message(response="utter_ask_pizza_amount_ack_size")
            elif requested_slot == "pizza_crust" and tracker.get_slot("pizza_crust") is not None:
                dispatcher.utter_message(response="utter_ask_pizza_amount_ack_crust")
            else:
                dispatcher.utter_message(response="utter_ask_pizza_amount_ack")
        else:
            dispatcher.utter_message(response="utter_ask_pizza_amount")
        return []
    
class ActionAskPizzaType(Action):
    def name(self):
        return 'action_ask_pizza_type'
    async def run(self, dispatcher, tracker, domain):
        last_intent = tracker.get_intent_of_latest_message()
        requested_slot = tracker.get_slot("requested_slot")
        if requested_slot == "pizza_type" and last_intent not in ["request_pizza_crusts", "request_pizza_sizes", "request_pizza_types", "request_delivery_areas", "request_payment_methods", "stop_order", "explain", "response_negative", "bot_challenge", "item_change", "item_change_request_without_entity", "nevermind", "book_table"]:
            dispatcher.utter_message(response="utter_ask_pizza_type_again")
            return []
        if last_intent == "item_start_generic":
            if requested_slot == "pizza_size" and tracker.get_slot("pizza_size") is not None:
                dispatcher.utter_message(response="utter_ask_pizza_type_ack_size")
            elif requested_slot == "pizza_amount" and tracker.get_slot("pizza_amount") is not None:
                dispatcher.utter_message(response="utter_ask_pizza_type_ack_amount")
            elif requested_slot == "pizza_crust" and tracker.get_slot("pizza_crust") is not None:
                dispatcher.utter_message(response="utter_ask_pizza_type_ack_crust")
            else:
                dispatcher.utter_message(response="utter_ask_pizza_type_ack")
        else:
            dispatcher.utter_message(response="utter_ask_pizza_type")
        return []
    
class ActionAskPizzaSize(Action):
    def name(self):
        return 'action_ask_pizza_size'
    async def run(self, dispatcher, tracker, domain):
        last_intent = tracker.get_intent_of_latest_message()
        requested_slot = tracker.get_slot("requested_slot")
        if requested_slot == "pizza_size" and last_intent not in ["request_pizza_crusts", "request_pizza_sizes", "request_pizza_types", "request_delivery_areas", "request_payment_methods", "stop_order", "explain", "response_negative", "bot_challenge", "item_change", "item_change_request_without_entity", "nevermind", "book_table"]:
            dispatcher.utter_message(response="utter_ask_pizza_size_again")
            return []
        if last_intent == "item_start_generic":
            if requested_slot == "pizza_type" and tracker.get_slot("pizza_type") is not None:
                dispatcher.utter_message(response="utter_ask_pizza_size_ack_type")
            elif requested_slot == "pizza_amount" and tracker.get_slot("pizza_amount") is not None:
                dispatcher.utter_message(response="utter_ask_pizza_size_ack_amount")
            elif requested_slot == "pizza_size" and tracker.get_slot("pizza_size") is not None:
                dispatcher.utter_message(response="utter_ask_pizza_size_ack_size")
            elif requested_slot == "pizza_crust" and tracker.get_slot("pizza_crust") is not None:
                dispatcher.utter_message(response="utter_ask_pizza_size_ack_crust")
            else:
                dispatcher.utter_message(response="utter_ask_pizza_size_ack")
        else:
            dispatcher.utter_message(response="utter_ask_pizza_size")
        return[]
    
class ActionAskPizzaCrust(Action):
    def name(self):
        return 'action_ask_pizza_crust'
    async def run(self, dispatcher, tracker, domain):
        last_intent = tracker.get_intent_of_latest_message()
        requested_slot = tracker.get_slot("requested_slot")
        if requested_slot == "pizza_crust" and last_intent not in ["request_pizza_crusts", "request_pizza_sizes", "request_pizza_types","request_delivery_areas", "request_payment_methods", "stop_order", "explain", "response_negative", "bot_challenge", "item_change", "item_change_request_without_entity", "nevermind", "book_table"]:
            dispatcher.utter_message(response="utter_ask_pizza_crust_again")
            return []
        if last_intent == "item_start_generic":
            if requested_slot == "pizza_type" and tracker.get_slot("pizza_type") is not None:
                dispatcher.utter_message(response="utter_ask_pizza_crust_ack_type")
            elif requested_slot == "pizza_size" and tracker.get_slot("pizza_size") is not None:
                dispatcher.utter_message(response="utter_ask_pizza_crust_ack_size")
            elif requested_slot == "pizza_amount" and tracker.get_slot("pizza_amount") is not None:
                dispatcher.utter_message(response="utter_ask_pizza_crust_ack_amount")
            else:
                dispatcher.utter_message(response="utter_ask_pizza_crust_ack")
        else:
            dispatcher.utter_message(response="utter_ask_pizza_crust")
        return[]
    
class ActionChangeOrder(Action):
    def name(self):
        return 'action_change_order'
    async def run(self, dispatcher, tracker: Tracker, domain):
        pizza_size = tracker.get_slot("pizza_size")
        pizza_type = tracker.get_slot("pizza_type")
        pizza_amount = tracker.get_slot("pizza_amount")
        pizza_crust = tracker.get_slot("pizza_crust")
        
        pizza_size_changed = next(tracker.get_latest_entity_values("pizza_size"), None)
        pizza_type_changed = next(tracker.get_latest_entity_values("pizza_type"), None)
        pizza_amount_changed = next(tracker.get_latest_entity_values("pizza_amount"), None)
        pizza_crust_changed = next(tracker.get_latest_entity_values("pizza_crust"), None)
        
        if pizza_size is None and pizza_type is None and pizza_amount is None and pizza_crust is None:
            dispatcher.utter_message(response="utter_warning_nothing_to_change")
            return [SlotSet("modify_order", None)]
        changes_string = []
        if pizza_size_changed:
            pizza_size = pizza_size_changed
            changes_string.append(f"the pizza size to {pizza_size}")
        if pizza_type_changed:
            pizza_type = pizza_type_changed
            changes_string.append(f"the pizza type to {pizza_type}")
        if pizza_amount_changed:
            pizza_amount = pizza_amount_changed
            changes_string.append(f"the amount of pizzas to {pizza_amount}")
        if pizza_crust_changed:
            pizza_crust = pizza_crust_changed
            changes_string.append(f"the crust to {pizza_crust}")
        if len(changes_string) > 0:
            if len(changes_string) > 1:
                changes_string[-1] = "and " + changes_string[-1]
            total_changes = "Alright, I've changed " + ", ".join(changes_string) + "."
            dispatcher.utter_message(text=total_changes)
        return [
            SlotSet("pizza_type", pizza_type),
            SlotSet("pizza_size", pizza_size),
            SlotSet("pizza_amount", pizza_amount),
            SlotSet("pizza_crust", pizza_crust),
            SlotSet("modify_order", None),
            SlotSet("current_order", None)
        ]

class ValidataDeliveryForm(FormValidationAction):
    def name(self) -> Text:
        return "validate_delivery_form"
    async def validate_client_name(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> Dict[Text, Any]:
        if isinstance(slot_value, str):
            return {"client_name": slot_value}
        elif isinstance(slot_value, list):
            if len(slot_value) > 0:
                concatenated_slot = ", ".join(slot_value)
                return {"client_name": concatenated_slot}
            else:
                dispatcher.utter_message(text="Please tell me your name.")
                return {"client_name": None}
    async def validate_phone_number(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> Dict[Text, Any]:
        if isinstance(slot_value, str):
            phone_pattern = re.compile(r"^\+(\d{1,3})\s(\d{6,15})$|^\d{10,15}$")
            if phone_pattern.match(slot_value):
                return {"client_phone_number": slot_value}
            else:
                dispatcher.utter_message(text="Please provide a valid phone number. Examples: +39 342626595, +046 514143, 340154156")
                return {"client_phone_number": None}
        elif isinstance(slot_value, list):
            if len(slot_value) > 0:
                concatenated_slot = ", ".join(slot_value)
                return {"client_phone_number": concatenated_slot}
            else:
                dispatcher.utter_message(text="Please tell me your phone number.")
                return {"client_phone_number": None}
    async def validate_client_address(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> Dict[Text, Any]:
        if tracker.active_loop.get('name') != "delivery_form":
            dispatcher.utter_message(text="We'll get to the delivery in a moment.")
            return {"client_address": None}
        if isinstance(slot_value, str):
            return {"client_address": slot_value}
        elif isinstance(slot_value, list):
            if len(slot_value) > 0:
                concatenated_slot = ", ".join(slot_value)
                return {"client_address": concatenated_slot}
            else:
                dispatcher.utter_message(text="Please tell me your address.")
                return {"client_address": None}
    async def validate_client_payment(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> Dict[Text, Any]:
        if tracker.active_loop.get('name') != "delivery_form":
            dispatcher.utter_message(text="We'll get to the payment later.")
            return {"client_payment": None}
        if isinstance(slot_value, str):
            if slot_value.lower() in ["cash", "card"]:
                return {"client_payment": slot_value}
            else:
                dispatcher.utter_message(text="I'm sorry, we accept only cash or card as payment methods.")
                return {"client_payment": None}
        elif isinstance(slot_value, list):
            if len(slot_value) > 0:
                concatenated_slot = ", ".join(slot_value)
                return {"client_payment": concatenated_slot}
            else:
                dispatcher.utter_message(text="Please tell me your payment method.")
                return {"client_payment": None}
            
class ValidateTakeawayForm(FormValidationAction):
    def name(self) -> Text:
        return "validate_takeaway_form"
    async def validate_client_name(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> Dict[Text, Any]:
        if isinstance(slot_value, str):
            return {"client_name": slot_value}
        elif isinstance(slot_value, list):
            if len(slot_value) > 0:
                concatenated_slot = ", ".join(slot_value)
                return {"client_name": concatenated_slot}
            else:
                dispatcher.utter_message(text="Please tell me your name.")
                return {"client_name": None}
    async def validate_phone_number(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> Dict[Text, Any]:
        if isinstance(slot_value, str):
            phone_pattern = re.compile(r"^\+(\d{1,3})\s(\d{6,15})$|^\d{10,15}$")
            if phone_pattern.match(slot_value):
                return {"client_phone_number": slot_value}
            else:
                dispatcher.utter_message(text="Please provide a valid phone number. Examples: +39 342626595, +046 514143, 340154156")
                return {"client_phone_number": None}
        elif isinstance(slot_value, list):
            if len(slot_value) > 0:
                concatenated_slot = ", ".join(slot_value)
                return {"client_phone_number": concatenated_slot}
            else:
                dispatcher.utter_message(text="Please tell me your phone number.")
                return {"client_phone_number": None}
            
class ActionClientNameMapping(Action):
    def name(self):
        return "action_client_name_mapping"
    async def run(self, dispatcher, tracker, domain):
        last_intent = tracker.get_intent_of_latest_message()
        if last_intent == "client_name" or last_intent == "welcome_greet":
            client_name = tracker.get_slot("client_name")
            ent_client_name = next(tracker.get_latest_entity_values("person_name"), None)
            if ent_client_name is None:
                return []
            else:
                if client_name is None:
                    return [SlotSet("client_name", ent_client_name)]
                else:
                    return [SlotSet("client_name", client_name)]
        return []
    
class ActionClientPhoneNumberMapping(Action):
    def name(self):
        return "action_client_phone_number_mapping"
    async def run(self, dispatcher, tracker, domain):
        last_intent = tracker.get_intent_of_latest_message()
        if last_intent == "client_phone_number":
            client_phone_number = tracker.get_slot("client_phone_number")
            ent_client_phone_number = next(tracker.get_latest_entity_values("client_phone_number"), None)
            if ent_client_phone_number is None:
                return []
            else:
                if client_phone_number is None:
                    return [SlotSet("client_phone_number", ent_client_phone_number)]
                else:
                    return [SlotSet("client_phone_number", client_phone_number)]
        return []
    
class ActionAddressMapping(Action):
    def name(self):
        return "action_address_mapping"
    async def run(self, dispatcher, tracker, domain):
        last_intent = tracker.get_intent_of_latest_message()
        if tracker.active_loop.get('name') != "delivery_form":
            dispatcher.utter_message(text="We'll get to the delivery later.")
        if last_intent == "client_address":
            client_address = tracker.get_slot("client_address")
            ent_client_address = next(tracker.get_latest_entity_values("client_address"), None)
            if ent_client_address is None:
                return []
            else:
                if client_address is None:
                    return [SlotSet("client_address", ent_client_address)]
                else:
                    return [SlotSet("client_address", client_address)]
        return []
    
class ActionPaymentMapping(Action):
    def name(self):
        return "action_payment_mapping"
    async def run(self, dispatcher, tracker, domain):
        last_intent = tracker.get_intent_of_latest_message()
        if tracker.active_loop.get('name') != "delivery_form":
            dispatcher.utter_message(text="We'll get to the payment later.")
        if last_intent == "client_payment":
            client_payment = tracker.get_slot("client_payment")
            ent_client_payment = next(tracker.get_latest_entity_values("client_payment"), None)
            if ent_client_payment is None:
                return []
            else:
                if client_payment is None:
                    return [SlotSet("client_payment", ent_client_payment)]
                else:
                    return [SlotSet("client_payment", client_payment)]
        return []
    
class ActionAskClientName(Action):
    def name(self):
        return 'action_ask_client_name'
    async def run(self, dispatcher, tracker, domain):
        last_intent = tracker.get_intent_of_latest_message()
        active_loop = tracker.active_loop.get('name')
        requested_slot = tracker.get_slot("requested_slot")
        if requested_slot == "client_name" and last_intent not in ["delivery_change", "delivery_change_request_without_entity", "item_change_request_without_entity", "stop_order", "explain", "response_negative", "bot_challenge", "nevermind", "book_table"]:
            dispatcher.utter_message(response="utter_ask_client_name_again")
            return []
        if active_loop == "delivery_form":
            if requested_slot == "client_address" and tracker.get_slot("client_address") is not None:
                dispatcher.utter_message(response="utter_ask_client_name_ack_address")
            elif requested_slot == "client_payment" and tracker.get_slot("client_payment") is not None:
                dispatcher.utter_message(response="utter_ask_client_name_ack_payment")
            elif requested_slot == "client_phone_number" and tracker.get_slot("client_phone_number") is not None:
                dispatcher.utter_message(response="utter_ask_client_name_ack_phone_number")
            else:
                dispatcher.utter_message(response="utter_ask_client_name_ack_delivery")
        elif active_loop == "takeaway_form":
            dispatcher.utter_message(response="utter_ask_client_name_ack_takeaway")
        else:
            dispatcher.utter_message(response="utter_ask_client_name")
        return []
    
class ActionAskClientPhoneNumber(Action):
    def name(self):
        return 'action_ask_client_phone_number'
    async def run(self, dispatcher, tracker, domain):
        last_intent = tracker.get_intent_of_latest_message()
        active_loop = tracker.active_loop.get('name')
        requested_slot = tracker.get_slot("requested_slot")
        if requested_slot == "client_phone_number" and last_intent not in ["delivery_change", "delivery_change_request_without_entity", "item_change_request_without_entity", "stop", "verbose", "response_negative", "bot"]:
            dispatcher.utter_message(response="utter_ask_client_phone_number_again")
            return []
        if active_loop == "delivery_form":
            if requested_slot == "client_address" and tracker.get_slot("client_address") is not None:
                dispatcher.utter_message(response="utter_ask_client_phone_number_ack_address")
            elif requested_slot == "client_payment" and tracker.get_slot("client_payment") is not None:
                dispatcher.utter_message(response="utter_ask_client_phone_number_ack_payment")
            elif requested_slot == "client_name" and tracker.get_slot("client_name") is not None:
                dispatcher.utter_message(response="utter_ask_client_phone_number_ack_name")
            else:
                dispatcher.utter_message(response="utter_ask_client_phone_number_ack_delivery")
        elif active_loop == "takeaway_form":
            dispatcher.utter_message(response="utter_ask_client_phone_number_ack_takeaway")
        else:
            dispatcher.utter_message(response="utter_ask_client_phone_number")
        return []
    
class ActionAskClientAddress(Action):
    def name(self):
        return 'action_ask_client_address'
    async def run(self, dispatcher, tracker, domain):
        last_intent = tracker.get_intent_of_latest_message()
        requested_slot = tracker.get_slot("requested_slot")
        active_loop = tracker.active_loop.get('name')
        if requested_slot == "client_address" and last_intent not in ["delivery_change", "delivery_change_request_without_entity", "item_change_request_without_entity", "request_pizza_crusts", "request_pizza_sizes", "request_pizza_types", "request_delivery_areas", "request_payment_methods", "stop_order", "explain", "response_negative", "bot_challenge", "nevermind", "book_table"]:
            dispatcher.utter_message(response="utter_ask_client_address_again")
            return []
        if last_intent in ["client_name", "client_address", "client_payment"]:
            if requested_slot == "client_payment" and tracker.get_slot("client_payment") is not None:
                dispatcher.utter_message(response="utter_ask_client_address_ack_payment")
            elif requested_slot == "client_name" and tracker.get_slot("client_name") is not None:
                dispatcher.utter_message(response="utter_ask_client_address_ack_name")
            elif requested_slot == "client_phone_number" and tracker.get_slot("client_phone_number") is not None:
                dispatcher.utter_message(response="utter_ask_client_address_ack_phone_number")
            else:
                dispatcher.utter_message(response="utter_ask_client_address_ack")
        else:
            dispatcher.utter_message(response="utter_ask_client_address")
        return []
    
class ActionAskClientPayment(Action):
    def name(self):
        return 'action_ask_client_payment'
    async def run(self, dispatcher, tracker, domain):
        last_intent = tracker.get_intent_of_latest_message()
        requested_slot = tracker.get_slot("requested_slot")
        active_loop = tracker.active_loop.get('name')
        if requested_slot == "client_payment" and last_intent not in ["delivery_change", "delivery_change_request_without_entity",  "item_change_request_without_entity", "request_pizza_crusts", "request_pizza_sizes", "request_pizza_types", "request_payment_methods", "stop", "verbose", "response_negative", "bot"]:
            dispatcher.utter_message(response="utter_ask_client_payment_again")
            return []
        if last_intent in ["client_name", "client_address", "client_payment"]:
            if requested_slot == "client_name" and tracker.get_slot("client_name") is not None:
                dispatcher.utter_message(response="utter_ask_client_payment_ack_name")
            elif requested_slot == "client_address" and tracker.get_slot("client_address") is not None:
                dispatcher.utter_message(response="utter_ask_client_payment_ack_address")
            elif requested_slot == "client_phone_number" and tracker.get_slot("client_phone_number") is not None:
                dispatcher.utter_message(response="utter_ask_client_payment_ack_phone_number")
            else:
                dispatcher.utter_message(response="utter_ask_client_payment_ack")
        else:
            dispatcher.utter_message(response="utter_ask_client_payment")
        return []
    
class ActionConfirmDelivery(Action):
    def name(self):
        return 'action_confirm_delivery'
    async def run(self, dispatcher, tracker, domain):
        client_name = tracker.get_slot("client_name")
        client_address = tracker.get_slot("client_address")
        client_payment = tracker.get_slot("client_payment")
        client_phone_number = tracker.get_slot("client_phone_number")
        time = tracker.get_slot("time")
        message = f"Perfect! We need that you confirm all the informations: the order will be for {client_name}, it will be delivered at {time} to {client_address}. The payment method is {client_payment}. In case of problem we will contact at {client_phone_number}."
        dispatcher.utter_message(text=message)
        return []
    
class ActionConfirmTakeaway(Action):
    def name(self):
        return 'action_confirm_takeaway'
    async def run(self, dispatcher, tracker, domain):
        client_name = tracker.get_slot("client_name")
        client_phone_number = tracker.get_slot("client_phone_number")
        time = tracker.get_slot("time")
        message = f"Perfect! We need that you confirm all the informations: the order will be for {client_name} at {time} to take away. In case of problem we will contact at {client_phone_number}."
        dispatcher.utter_message(text=message)
        return []
    
class ActionChangeDelivery(Action):
    def name(self):
        return 'action_change_delivery'
    async def run(self, dispatcher, tracker, domain):
        client_name = tracker.get_slot("client_name")
        client_phone_number = tracker.get_slot("client_phone_number")
        client_address = tracker.get_slot("client_address")
        client_payment = tracker.get_slot("client_payment")
        
        client_name_changed = next(tracker.get_latest_entity_values("client_name"), None)
        client_phone_number_changed = next(tracker.get_latest_entity_values("client_phone_number"), None)
        client_address_changed = next(tracker.get_latest_entity_values("client_address"), None)
        client_payment_changed = next(tracker.get_latest_entity_values("client_payment"), None)
        
        if client_name is None and client_address is None and client_payment is None:
            dispatcher.utter_message(response="utter_warning_nothing_to_change_delivery")
            return []
        
        changes_string = []
        if client_name_changed:
            client_name = client_name_changed
            changes_string.append(f"the name to {client_name}")
        if client_phone_number_changed:
            client_phone_number = client_phone_number_changed
            changes_string.append(f"the phone number to {client_phone_number}")
        if client_address_changed:
            client_address = client_address_changed
            changes_string.append(f"the address to {client_address}")
        if client_payment_changed:
            client_payment = client_payment_changed
            changes_string.append(f"the payment method to {client_payment}")
        if len(changes_string) > 0:
            if len(changes_string) > 1:
                changes_string[-1] = "and " + changes_string[-1]
            total_changes = "Alright, I've changed " + ", ".join(changes_string) + "."
            dispatcher.utter_message(text=total_changes)
        return [
            SlotSet("client_name", client_name),
            SlotSet("client_phone_number", client_phone_number),
            SlotSet("client_address", client_address),
            SlotSet("client_payment", client_payment),
        ]
        
class ActionChangeTakeAway(Action):
    def name(self):
        return 'action_change_takeaway'
    async def run(self, dispatcher, tracker, domain):
        client_name = tracker.get_slot("client_name")
        client_phone_number = tracker.get_slot("client_phone_number")
        
        client_name_changed = next(tracker.get_latest_entity_values("client_name"), None)
        client_phone_number_changed = next(tracker.get_latest_entity_values("client_phone_number"), None)
        
        if client_name is None and client_phone_number is None:
            dispatcher.utter_message(response="utter_warning_nothing_to_change_takeaway")
            return []
        
        changes_string = []
        if client_name_changed:
            client_name = client_name_changed
            changes_string.append(f"the name to {client_name}")
        if client_phone_number_changed:
            client_phone_number = client_phone_number_changed
            changes_string.append(f"the phone number to {client_phone_number}")
        if len(changes_string) > 0:
            if len(changes_string) > 1:
                changes_string[-1] = "and " + changes_string[-1]
            total_changes = "Ok, I've changed " + ", ".join(changes_string) + "."
            dispatcher.utter_message(text=total_changes)
        return [
            SlotSet("client_name", client_name),
            SlotSet("client_phone_number", client_phone_number),
        ]

class ActionTimeMapping(Action):
    def name(self):
        return "action_time_mapping"
    async def run(self, dispatcher, tracker, domain):
        last_intent = tracker.get_intent_of_latest_message()
        if last_intent == "time":
            time = tracker.get_slot("time")
            ent_time = next(tracker.get_latest_entity_values("time"), None)
            if ent_time is None:
                return []
            else:
                if time is None:
                    return [SlotSet("time", ent_time)]
                else:
                    return [SlotSet("time", time)]
        return []

class ActionAskTime(Action):
    def name(self):
        return 'action_ask_time'
    async def run(self, dispatcher, tracker, domain):
        last_intent = tracker.get_intent_of_latest_message()
        requested_slot = tracker.get_slot("requested_slot")
        if requested_slot == "time" and last_intent not in ["time_change", "time_change_request_without_entity", "stop", "verbose", "response_negative", "bot"]:
            dispatcher.utter_message(response="utter_ask_time_again")
            return []
		
        takeaway_flag = tracker.get_slot("takeaway_flag")
        if takeaway_flag:
            if last_intent in ["response_negative", "response_positive"]:
                dispatcher.utter_message(response="utter_ask_time_takeaway_ack")
            else:
                dispatcher.utter_message(response="utter_ask_time_takeaway")
        else:
            if last_intent in ["response_negative", "response_positive"]:
                dispatcher.utter_message(response="utter_ask_time_delivery_ack")
            else:
                dispatcher.utter_message(response="utter_ask_time_delivery")
        return []
    
class ActionChangeTime(Action):
    def name(self):
        return 'action_change_time'
    async def run(self, dispatcher, tracker, domain):
        time = tracker.get_slot("time")
        time_changed = next(tracker.get_latest_entity_values("time"), None)
        if time is None:
            dispatcher.utter_message(response="utter_warning_nothing_to_change_time")
            return []
        changes_string = []
        if time_changed:
            time = time_changed
            changes_string.append(f"the time to {time}")
        if len(changes_string) > 0:
            if len(changes_string) > 1:
                changes_string[-1] = "and " + changes_string[-1]
            total_changes = "Alright, I changed " + ", ".join(changes_string) + "."
            dispatcher.utter_message(text=total_changes)
        return [SlotSet("time", time)]

class ActionConfirmTime(Action):
    def name(self):
        return 'action_confirm_time'
    async def run(self, dispatcher, tracker, domain):
        time = tracker.get_slot("time")
        takeaway_flag = tracker.get_slot("takeaway_flag")
        if takeaway_flag:
            message = f"Can you confirm that the order will be picked up at {time}?"
        else:
            message = f"Can you confirm that the order will be delivered at {time}?"
            dispatcher.utter_message(text=message)
        return []