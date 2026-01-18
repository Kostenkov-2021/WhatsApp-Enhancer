
import ui
import queueHandler
from threading import Timer
import config
from nvwave import playWaveFile
import os
import controlTypes
import api

# Media path helper
# Assumes folder structure: appModules/../media
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "media"))

class TitleObserver:
	"""Monitors chat title changes (e.g., typing status, online)."""
	app = None
	active = False
	paused = False
	interval = 0.5
	last_value = None

	@classmethod
	def tick(cls):
		if not cls.active or cls.paused: return
		try:
			if not cls.app:
				cls.paused = True
				return

			title_el = cls.app.get_title_element()
			if not title_el:
				Timer(cls.interval, cls.tick).start()
				return

			# Status extraction logic
			# Expected structure: children[2] = Name, children[3] = Status
			if title_el.childCount < 3: 
				Timer(cls.interval, cls.tick).start()
				return

			# Only process if in foreground
			if not title_el.isInForeground:
				Timer(cls.interval, cls.tick).start()
				return

			chat_name = title_el.children[2].name
			sub_title = title_el.children[3].name if title_el.childCount > 3 else ""
			
			last_value = cls.last_value or ("", "")
			
			# Check for subtitle changes within the same chat
			if sub_title != last_value[1]:
				if chat_name == last_value[0] and sub_title:
					# Clean separator characters if present
					clean_subtitle = sub_title.replace("‎∶‎", "‎:‎")
					queueHandler.queueFunction(queueHandler.eventQueue, ui.message, clean_subtitle)
				cls.last_value = (chat_name, sub_title)
			
			Timer(cls.interval, cls.tick).start()
		except:
			cls.paused = True

	@classmethod
	def toggle(cls, app):
		if not cls.active:
			cls.app = app
			cls.paused = False
			cls.active = True
			Timer(cls.interval, cls.tick).start()
			return True
		else:
			cls.active = False
			return False

	@classmethod
	def restore(cls, app):
		cls.paused = False
		cls.active = True
		cls.app = app
		cls.last_value = None
		Timer(cls.interval, cls.tick).start()

class ChatObserver:
	"""Monitors new messages in the currently open chat."""
	active = False
	paused = False
	interval = 0.5
	app = None
	last_message_info = None 

	@classmethod
	def tick(cls):
		if not cls.active or cls.paused: return
		try:
			list_el = cls.app.get_messages_element()
			if not list_el or not list_el.lastChild:
				Timer(cls.interval, cls.tick).start()
				return

			last_msg = list_el.lastChild
			
			# Use UIA grouping info to detect new messages
			try:
				total_count = last_msg.positionInfo.get("similarItemsInGroup")
				index = last_msg.positionInfo.get("indexInGroup")
			except:
				total_count = None
				index = None

			if not last_msg.isInForeground:
				Timer(cls.interval, cls.tick).start()
				return

			last_saved = cls.last_message_info or ("", 0)
			
			# If message count changed and we are at the last index
			if total_count and total_count != last_saved[1] and total_count == index:
				
				# Skip own messages
				is_my_msg = cls.app.is_own_message(last_msg)
				
				if not is_my_msg:
					cls.app.focus_and_read_message(last_msg)
					sound_path = os.path.join(BASE_DIR, "whatsapp_incoming.wav")
					if os.path.exists(sound_path):
						playWaveFile(sound_path)
				
				cls.last_message_info = ("CurrentChat", total_count)
			
			Timer(cls.interval, cls.tick).start()
		except:
			pass

	@classmethod
	def toggle(cls, app):
		conf = config.conf["WhatsAppEnhancer"]
		if not conf["automaticReadingOfNewMessages"]:
			conf["automaticReadingOfNewMessages"] = True
			cls.active = True
			cls.paused = False
			cls.app = app
			Timer(cls.interval, cls.tick).start()
			return True
		else:
			conf["automaticReadingOfNewMessages"] = False
			cls.active = False
			return False

	@classmethod
	def restore(cls, app):
		cls.paused = False
		cls.active = True
		cls.app = app
		cls.last_message_info = None
		Timer(cls.interval, cls.tick).start()

class ProgressObserver:
	"""Monitors progress bar updates (e.g., file downloads)."""
	active = False
	interval = 1.0
	progress_obj = None
	last_val = None

	@classmethod
	def start(cls):
		obj = api.getFocusObject()
		cls.progress_obj = None
		if obj.childCount > 0:
			for child in obj.children:
				if child.role == controlTypes.Role.PROGRESSBAR:
					cls.progress_obj = child
					break
		
		if cls.progress_obj:
			cls.active = True
			cls.tick()

	@classmethod
	def tick(cls):
		if not cls.active or not cls.progress_obj: return
		
		try:
			val = cls.progress_obj.value or cls.progress_obj.name
			if not cls.last_val or cls.last_val != val:
				ui.message(f"Progress: {val}")
				cls.last_val = val
			Timer(cls.interval, cls.tick).start()
		except:
			cls.active = False
