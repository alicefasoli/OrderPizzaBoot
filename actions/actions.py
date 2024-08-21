from typing import Any, Coroutine, Text, Dict, List
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet, FollowupAction, Restarted
from rasa.shared.core.events import Event
from typing import Text, List, Any, Dict
from rasa_sdk import Tracker, FormValidationAction
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.types import DomainDict
import re
import ast
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
            menu_text = "Here is our menu:\n"
            for row in results:
                menu_text += f"{row[0]} \n\t* Small: {row[1]:.2f}$ \n\t* Medium: {row[2]:.2f}$ \n\t* Large: {row[3]:.2f}$ \n\t* Extra Large: {row[4]:.2f}$\n"
            menu_text += "\nNote that we have also different type of toppings and crusts that you can add. This would add to the order 1$ for each topping and from 1$ to 3$ for different crusts."
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
                crust_menu_text = f"Here is our crusts price:{results[0]:.2f}$\n"
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
        if pizza_type is None:
            dispatcher.utter_message(text="Please provide the pizza type.")
            return []

        connection = sqlite3.connect('menu.db')
        cursor = connection.cursor()
        query = '''
            SELECT i.ingredient
            FROM ingredients i
            JOIN pizza_ingredients pi ON i.id = pi.ingredient_id
            JOIN menu m ON pi.pizza_id = m.id
            WHERE m.name LIKE ?
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
        return [SlotSet("pizza_type", None)]

class ActionGetAvailableToppings(Action):
    def name(self) -> Text:
        return "action_get_available_toppings"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        connection = sqlite3.connect('menu.db')
        cursor = connection.cursor()

        cursor.execute("SELECT ingredient FROM ingredients")
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
        return [Restarted(), FollowupAction("action_listen")]
    
class ActionConfirmOrder(Action):
    def name(self):
        return 'action_confirm_order'
    async def run(self, dispatcher, tracker, domain):
        pizza_size = tracker.get_slot("pizza_size")          
        pizza_type = tracker.get_slot("pizza_type")
        pizza_amount = tracker.get_slot("pizza_amount")
        pizza_crust = tracker.get_slot("pizza_crust")        
        order_details = ""
        toppings = tracker.get_slot("pizza_topping")
        if toppings is not None or toppings != "none":
            toppings = "with " + toppings
            order_details += f"{pizza_amount} {pizza_size} {pizza_crust} crust {pizza_type} {toppings}"
        else:
            order_details += f"{pizza_amount} {pizza_size} {pizza_crust} crust {pizza_type}"
            
        last_intent = tracker.get_intent_of_latest_message()
        if last_intent == "current_order":
            dispatcher.utter_message(text="Your order is " + order_details)
            return []
        else:
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
        second_pizza_topping = tracker.get_slot("second_pizza_topping")

        next_pizza_type = None
        next_pizza_size = None
        next_pizza_amount = None
        next_pizza_crust = None
        next_pizza_topping = None
        events = []
        if second_pizza_type is not None:
            next_pizza_type = second_pizza_type.pop(0)
            events += [SlotSet("pizza_type", next_pizza_type), SlotSet("second_pizza_type", second_pizza_type if len(second_pizza_type) > 0 else None)]
        else:
            events += [SlotSet("pizza_type", None)]
        if second_pizza_size is not None:
            next_pizza_size = second_pizza_size.pop(0)
            events += [SlotSet("pizza_size", next_pizza_size), SlotSet("second_pizza_size", second_pizza_size if len(second_pizza_size) > 0 else None)]
        else:
            events += [SlotSet("pizza_size", None)]
        if second_pizza_amount is not None:
            next_pizza_amount = second_pizza_amount.pop(0)
            events += [SlotSet("pizza_amount", next_pizza_amount), SlotSet("second_pizza_amount", second_pizza_amount if len(second_pizza_amount) > 0 else None)]
        else:
            events += [SlotSet("pizza_amount", None)]
        if second_pizza_crust is not None:
            next_pizza_crust = second_pizza_crust.pop(0)
            events +=  [SlotSet("pizza_crust", next_pizza_crust), SlotSet("second_pizza_crust", second_pizza_crust if len(second_pizza_crust) > 0 else None)]
        else:
            events += [SlotSet("pizza_crust", None)]
        if second_pizza_topping is not None:
            next_pizza_topping = second_pizza_topping.pop(0)
            events +=  [SlotSet("pizza_topping", next_pizza_topping), SlotSet("second_pizza_topping", second_pizza_topping if len(second_pizza_topping) > 0 else None)]
        else:
            events += [SlotSet("pizza_topping", None)]
        if next_pizza_type is not None or next_pizza_size is not None or next_pizza_amount is not None or next_pizza_crust is not None:
            next_order= ""
            next_order += f"{next_pizza_amount} " if next_pizza_amount is not None else ""
            next_order += f"{next_pizza_size} " if next_pizza_size is not None else ""
            next_order += f"{next_pizza_crust} crust " if next_pizza_crust is not None else ""
            next_order += f"{next_pizza_type}" if next_pizza_type is not None else ""
            next_order += f"{next_pizza_topping}" if next_pizza_topping is not None else ""
            dispatcher.utter_message(text=f"Alright, let's go through the next {next_order} pizza.")
        return [FollowupAction("utter_something_else")]
        
class ActionPizzaOrderAdd(Action):
    def name(self):
        return 'action_pizza_order_add'
    async def run(self, dispatcher, tracker, domain):
        numbers_dict = {
            "one": 1,
            "two": 2,
            "three": 3,
            "four": 4,
            "five": 5,
            "six": 6,
            "seven": 7,
            "eight": 8,
            "nine": 9,
            "ten": 10,
            "eleven": 11,
            "twelve": 12,
            "thirteen": 13,
            "fourteen": 14,
            "fifteen": 15,
            "sixteen": 16,
            "seventeen": 17,
            "eighteen": 18,
            "nineteen": 19,
            "twenty": 20
        }
        
        current_order = tracker.get_slot("current_order")
        if current_order is None:
            dispatcher.utter_message(text="Sorry, there is an error. You have no open order.")
            return []
        total_order = tracker.get_slot("total_order")
        if total_order is None:
            total_order = []
        total_order.extend(tracker.get_slot("current_order"))

        pizza_type = tracker.get_slot('pizza_type').lower()
        size = tracker.get_slot('pizza_size').lower()
        amount = tracker.get_slot('pizza_amount').lower()
        crust = tracker.get_slot('pizza_crust').lower()
        toppings =  tracker.get_slot('pizza_topping')
        
        total_price = tracker.get_slot("total_price")
        if total_price is None:
            total_price = 0
        else:
            total_price = int(total_price)
        
        if toppings == "no extra topping":
            n_toppings = 0
        else:
            n_toppings = 1
            
        if amount.lower() in numbers_dict:
            n_pizzas = numbers_dict[amount.lower()]
        else:
            n_pizzas = int(amount)
        
        try:
            connection = sqlite3.connect('menu.db')
            cursor = connection.cursor()
            if size == "small":
                query = 'SELECT price_small FROM menu WHERE name LIKE ?'
            elif size == "medium":
                query = 'SELECT price_medium FROM menu WHERE name LIKE ?'
            elif size == "large":
                query = 'SELECT price_large FROM menu WHERE name LIKE ?'
            elif size == "extra large":
                query = 'SELECT price_extra_large FROM menu WHERE name LIKE ?'
            cursor.execute(query, (pizza_type, ))
            pizza_price = cursor.fetchall()
            
            query2 = 'SELECT price FROM crust WHERE type LIKE ?'
            cursor.execute(query2, (crust,))
            crusts_price = cursor.fetchall()
            
            total_price += (int(pizza_price[0][0]) + int(crusts_price[0][0]) + n_toppings) * n_pizzas      
            dispatcher.utter_message(text=f"Your pizza(s) has been placed successfully! Your partial price is {total_price}$.")
            
            connection.close()
        except sqlite3.Error as e:
            print(f"An error occurred: {e}")
        
        return [SlotSet("total_order", total_order), 
                SlotSet("total_price", total_price), 
                SlotSet("pizza_type", None),
                SlotSet("pizza_size", None),
                SlotSet("pizza_amount", None), 
                SlotSet("pizza_crust", None),  
                SlotSet("pizza_topping", None), 
                SlotSet("current_order", None)
        ]

class ActionResetPizzaForm(Action):
    def name(self):
        return 'action_reset_pizza_form'
    async def run(self, dispatcher, tracker, domain):
        return[
            SlotSet("pizza_type", None),
            SlotSet("pizza_size", None),
            SlotSet("pizza_amount", None), 
            SlotSet("pizza_crust", None), 
            SlotSet("pizza_topping", None), 
            SlotSet("current_order", None)
        ]

class ActionOrderNumber(Action):
    def name(self):
        return 'action_order_number'
    async def run(self, dispatcher, tracker, domain):
        name_person = tracker.get_slot("client_name")
        number_person = tracker.get_slot("client_phone_number")
        order_number =  str(name_person + "_" + number_person)
        dispatcher.utter_message(text=f"Remember your order number {order_number}.")
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
            cursor.execute("SELECT ingredient FROM ingredients")
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
            pizza_topping = tracker.get_slot("pizza_topping")
            second_pizza_type = tracker.get_slot("second_pizza_type")
            second_pizza_size = tracker.get_slot("second_pizza_size")
            second_pizza_amount = tracker.get_slot("second_pizza_amount")
            second_pizza_crust = tracker.get_slot("second_pizza_crust")
            second_pizza_topping = tracker.get_slot("second_pizza_topping")
            if second_pizza_type is not None or second_pizza_size is not None or second_pizza_amount is not None or second_pizza_crust is not None or second_pizza_topping is not None:
                if second_pizza_type is not None and pizza_type is not None:
                    dispatcher.utter_message(text=f"Got it. For now, let’s stick to the {pizza_type} pizza.")
                elif second_pizza_size is not None and pizza_size is not None:
                    dispatcher.utter_message(text=f"Understood. Let's concentrate on the first {pizza_size} pizza.")
                elif second_pizza_amount is not None and pizza_amount is not None:
                    dispatcher.utter_message(text=f"Alright. We’ll focus on the first {pizza_amount} pizza for now.")
                elif second_pizza_crust is not None and pizza_crust is not None:
                    dispatcher.utter_message(text=f"Okay. We’ll handle the first {pizza_crust} pizza first.")
                elif pizza_topping is not None and second_pizza_topping is not None:
                    dispatcher.utter_message(text=f"Okay. We’ll handle the first {pizza_topping} pizza first.")
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
                dispatcher.utter_message(text="Please tell me a valid pizza type. This is not in the menu.")
                dispatcher.utter_message(text=f"Choose from this available pizzas: {self.get_menu()}")
                return {"pizza_type": None}
        elif isinstance(slot_value, list):
            if len(slot_value) > 0:
                concatenated_slot = ", ".join(slot_value)
                return {"pizza_type": concatenated_slot}
            else:
                dispatcher.utter_message(text="Please tell me a valid pizza type.")
                dispatcher.utter_message(text=f"Choose from this available pizzas: {self.get_menu()}")
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
                dispatcher.utter_message(text="Please tell me a valid amount.")
                dispatcher.utter_message(response="utter_inform_pizza_amount")
                return {"pizza_amount": None}
        elif isinstance(slot_value, list):
            if len(slot_value) > 0:
                concatenated_slot = ", ".join(slot_value)
                return {"pizza_amount": concatenated_slot}
            else:
                dispatcher.utter_message(text="Please tell me a valid amount.")
                dispatcher.utter_message(response="utter_inform_pizza_amount")
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
    def validate_pizza_topping(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> Dict[Text, Any]:
        """Validate the toppings slot, considering it as optional."""
        if slot_value == "none":
            return {"pizza_topping": "none"}

        valid_toppings = self.get_toppings()
        if isinstance(slot_value, str):
            if slot_value.lower() in valid_toppings:
                return {"pizza_topping": slot_value.lower()}
            else:
                dispatcher.utter_message(
                    text=f"The following topping is not recognized: {slot_value.lower()}. Please provide valid topping."
                )
                dispatcher.utter_message(text=f"Choose from this available toppings: {valid_toppings}")
                return {"pizza_topping": None}
    
class ActionTypeMapping(Action):
    def name(self) -> Text:
        return "action_type_mapping"
    async def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: DomainDict) -> Coroutine[Any, Any, List[Dict[Text, Any]]]:
        last_intent = tracker.get_intent_of_latest_message()
        if last_intent == "order_pizza_inform" or last_intent == "init_pizza_question": 
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
        if last_intent == "order_pizza_inform": 
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
        if last_intent == "order_pizza_inform": 
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
        if last_intent == "order_pizza_inform": 
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

class ActionToppingMapping(Action):
    def name(self) -> Text:
        return "action_topping_mapping"
    async def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: DomainDict) -> Coroutine[Any, Any, List[Dict[Text, Any]]]:
        last_intent = tracker.get_intent_of_latest_message()
        if last_intent == "order_pizza_inform": 
            pizza_topping = tracker.get_slot("pizza_topping")
            ent_pizza_topping = next(tracker.get_latest_entity_values("pizza_topping"), None)
            if ent_pizza_topping is None:
                return []
            else:
                if pizza_topping is None:
                    return [SlotSet("pizza_topping", ent_pizza_topping)]
                else:
                    return [SlotSet("pizza_topping", pizza_topping)]
        return []
 
class ActionAskPizzaAmount(Action):
    def name(self):
        return 'action_ask_pizza_amount'
    async def run(self, dispatcher, tracker, domain):
        dispatcher.utter_message(response="utter_ask_pizza_amount")
        return []
    
class ActionAskPizzaType(Action):
    def name(self):
        return 'action_ask_pizza_type'
    async def run(self, dispatcher, tracker, domain):
        dispatcher.utter_message(response="utter_ask_pizza_type")
        return []
    
class ActionAskPizzaSize(Action):
    def name(self):
        return 'action_ask_pizza_size'
    async def run(self, dispatcher, tracker, domain):
        dispatcher.utter_message(response="utter_ask_pizza_size")
        return []

class ActionAskPizzaCrust(Action):
    def name(self):
        return 'action_ask_pizza_crust'
    async def run(self, dispatcher, tracker, domain):
        dispatcher.utter_message(response="utter_ask_pizza_crust")
        return []
       
class ActionAskPizzaToppings(Action):
    def name(self):
        return 'action_ask_pizza_topping'
    async def run(self, dispatcher, tracker, domain):
        dispatcher.utter_message(response="utter_ask_pizza_topping")
        return []
    
class ActionChangeOrder(Action):
    def name(self):
        return 'action_change_order'
    async def run(self, dispatcher, tracker: Tracker, domain):
        pizza_size = tracker.get_slot("pizza_size")
        pizza_type = tracker.get_slot("pizza_type")
        pizza_amount = tracker.get_slot("pizza_amount")
        pizza_crust = tracker.get_slot("pizza_crust")
        pizza_topping = tracker.get_slot("pizza_topping")
        
        pizza_size_changed = next(tracker.get_latest_entity_values("pizza_size"), None)
        pizza_type_changed = next(tracker.get_latest_entity_values("pizza_type"), None)
        pizza_amount_changed = next(tracker.get_latest_entity_values("pizza_amount"), None)
        pizza_crust_changed = next(tracker.get_latest_entity_values("pizza_crust"), None)
        pizza_topping_changed = next(tracker.get_latest_entity_values("pizza_topping"), None)
        
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
        if pizza_topping_changed:
            pizza_topping = pizza_topping_changed
            changes_string.append(f"the toppings to {pizza_topping}")
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
            SlotSet("pizza_topping", pizza_topping),
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
    async def validate_client_phone_number(
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
    async def validate_client_phone_number(
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
            
class ActionNameMapping(Action):
    def name(self):
        return "action_name_mapping"
    async def run(self, dispatcher, tracker, domain):
        last_intent = tracker.get_intent_of_latest_message()
        if last_intent == "order_delivery" or last_intent == "order_takeaway":
            client_name = tracker.get_slot("client_name")
            ent_client_name = next(tracker.get_latest_entity_values("client_name"), None)
            if ent_client_name is None:
                return []
            else:
                if client_name is None:
                    return [SlotSet("client_name", ent_client_name)]
                else:
                    return [SlotSet("client_name", client_name)]
        return []
    
class ActionPhoneNumberMapping(Action):
    def name(self):
        return "action_phone_number_mapping"
    async def run(self, dispatcher, tracker, domain):
        last_intent = tracker.get_intent_of_latest_message()
        if last_intent == "order_delivery" or last_intent == "order_takeaway":
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
        if last_intent == "order_delivery":
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
        if last_intent == "order_delivery":
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
        dispatcher.utter_message(response="utter_ask_client_name")
        return []
    
class ActionAskClientPhoneNumber(Action):
    def name(self):
        return 'action_ask_client_phone_number'
    async def run(self, dispatcher, tracker, domain):
        dispatcher.utter_message(response="utter_ask_client_phone_number")
        return []
    
class ActionAskClientAddress(Action):
    def name(self):
        return 'action_ask_client_address'
    async def run(self, dispatcher, tracker, domain):
        dispatcher.utter_message(response="utter_ask_client_address")
        return []
    
class ActionAskClientPayment(Action):
    def name(self):
        return 'action_ask_client_payment'
    async def run(self, dispatcher, tracker, domain):
        dispatcher.utter_message(response="utter_ask_client_payment")
        dispatcher.utter_message(response="utter_inform_client_payment")
        return []
    
class ActionConfirmDelivery(Action):
    def name(self):
        return 'action_confirm_delivery'
    async def run(self, dispatcher, tracker, domain):
        client_name = tracker.get_slot("client_name")
        client_address = tracker.get_slot("client_address")
        client_payment = tracker.get_slot("client_payment")
        client_phone_number = tracker.get_slot("client_phone_number")
        message = f"Perfect! We need that you confirm all the informations: the order will be for {client_name}, to {client_address}. The payment method is {client_payment}. In case of problem we will contact at {client_phone_number}. Everything correct?"
        dispatcher.utter_message(text=message)
        return []
    
class ActionConfirmTakeaway(Action):
    def name(self):
        return 'action_confirm_takeaway'
    async def run(self, dispatcher, tracker, domain):
        client_name = tracker.get_slot("client_name")
        client_phone_number = tracker.get_slot("client_phone_number")
        message = f"Perfect! We need that you confirm all the informations: the order will be for {client_name} to take away. In case of problem we will contact at {client_phone_number}. Everything correct?"
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
        
        if client_name is None and client_address is None and client_payment is None and client_phone_number is None:
            dispatcher.utter_message(response="utter_warning_nothing_to_change")
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
            dispatcher.utter_message(response="utter_warning_nothing_to_change")
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
        time = tracker.get_slot("time")
        if time is None:
            takeaway_flag = tracker.get_slot("takeaway_flag")
            if takeaway_flag:
                dispatcher.utter_message(response="utter_time_takeaway")
                return []
            else:
                dispatcher.utter_message(response="utter_time_delivery")
                return []
            
        return []
    
class ActionChangeTime(Action):
    def name(self):
        return 'action_change_time'
    async def run(self, dispatcher, tracker, domain):
        time = tracker.get_slot("time")
        time_changed = next(tracker.get_latest_entity_values("time"), None)
        if time is None:
            dispatcher.utter_message(response="utter_warning_nothing_to_change")
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