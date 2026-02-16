import ui
import api
import controlTypes
from .wh_utils import find_elements_by_role, find_button_by_name, find_by_automation_id
import re

def set_focus_and_navigator(obj):
	if not obj: return False
	try:
		obj.setFocus()
		api.setNavigatorObject(obj)
		return True
	except:
		return False

def get_ia2_class(obj):
	try: return getattr(obj, "IA2Attributes", {}).get("class", "")
	except: return ""

def focus_chats(app_instance):
	if getattr(app_instance, "_chats_cache", None):
		try:
			target = app_instance._chats_cache
			if target.role == controlTypes.Role.LIST and target.firstChild:
				target = target.firstChild
			if set_focus_and_navigator(target): return
		except:
			app_instance._chats_cache = None
	root = app_instance.mainWindow or api.getForegroundObject()
	if not root: return
	for aid in ("ChatList", "Navigation", "ChatSearch", "Search"):
		found = find_by_automation_id(root, aid)
		if found:
			app_instance._chats_cache = found[0]
			target = found[0].firstChild if found[0].role == controlTypes.Role.LIST and found[0].firstChild else found[0]
			if set_focus_and_navigator(target): return
	lists = find_elements_by_role(root, controlTypes.Role.LIST)
	v = [l for l in lists if l.location and l.location.left < 450 and l.location.width < 500]
	if v:
		target = sorted(v, key=lambda x: x.location.left)[0]
		app_instance._chats_cache = target
		item = target.firstChild or target
		set_focus_and_navigator(item)

def focus_messages(app_instance):
	if getattr(app_instance, "_message_list_cache", None):
		try:
			target = app_instance._message_list_cache
			if target.role == controlTypes.Role.LIST and target.lastChild:
				target = target.lastChild
			if set_focus_and_navigator(target): return
		except:
			app_instance._message_list_cache = None
	if getattr(app_instance, "_composer_cache", None):
		try:
			c = app_instance._composer_cache
			target = c.parent.parent.parent.parent.parent.previous.lastChild.lastChild
			if target:
				app_instance._message_list_cache = target
				if set_focus_and_navigator(target.lastChild or target): return
		except:
			pass
	root = app_instance.mainWindow or api.getForegroundObject()
	if not root: return
	for aid in ("MessagesList", "Conversation", "MessageList"):
		found = find_by_automation_id(root, aid)
		if found:
			app_instance._message_list_cache = found[0]
			target = found[0].lastChild if found[0].role == controlTypes.Role.LIST and found[0].lastChild else found[0]
			set_focus_and_navigator(target)
			return
	lists = find_elements_by_role(root, controlTypes.Role.LIST)
	for l in lists:
		if "focusable-list-item" in get_ia2_class(l.firstChild or l):
			app_instance._message_list_cache = l
			set_focus_and_navigator(l.lastChild or l)
			return

def focus_composer(app_instance):
	if getattr(app_instance, "_composer_cache", None):
		if set_focus_and_navigator(app_instance._composer_cache): return
	root = app_instance.mainWindow or api.getForegroundObject()
	if not root: return
	for aid in ("Composer", "ChatTextInput", "MsgInput", "TextBox"):
		found = find_by_automation_id(root, aid)
		if found:
			app_instance._composer_cache = found[0]
			set_focus_and_navigator(found[0])
			return
	edits = find_elements_by_role(root, controlTypes.Role.EDITABLETEXT)
	for e in edits:
		if "fd365im1" in get_ia2_class(e):
			app_instance._composer_cache = e
			set_focus_and_navigator(e)
			return
	v = [e for e in edits if e.location and e.location.height > 0]
	if v:
		target = sorted(v, key=lambda x: x.location.top, reverse=True)[0]
		app_instance._composer_cache = target
		set_focus_and_navigator(target)
