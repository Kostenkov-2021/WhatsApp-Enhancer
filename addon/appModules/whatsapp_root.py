
import appModuleHandler
from scriptHandler import script
import ui
import api
import controlTypes
import config
import sys
import re
import logHandler
import speech
import speechViewer
import tones
import globalCommands
import addonHandler
import winUser

addonHandler.initTranslation()

sys.path.insert(0, ".")
from .text_window import TextWindow
from .wh_observers import TitleObserver, ChatObserver, ProgressObserver
from .wh_navigation import (
	perform_voice_call, 
	perform_video_call
)
from .wh_utils import find_by_automation_id, find_button_by_name

class AppModule(appModuleHandler.AppModule):
	disableBrowseModeByDefault = True
	mainWindow = None
	scriptCategory = _("WhatsApp Enhancer")
	
	_message_list_cache = None
	_composer_cache = None
	_chats_cache = None
	_title_element_cache = None

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self._last_spoken_text = ""
		self._last_spoken_lines = []
		self._review_cursor = 0
		self._review_line_index = 0
		self._is_reviewing = False
		self._original_speak = None
		self._patch_speech()
		try:
			conf = config.conf["WhatsAppEnhancer"]
			if conf.get("automaticReadingOfNewMessages") and not ChatObserver.active:
				ChatObserver.restore(self)
		except:
			pass

	def event_NVDAObject_init(self, obj):
		if obj.role == controlTypes.Role.SECTION:
			obj.role = controlTypes.Role.PANE
		try:
			ia2 = getattr(obj, "IA2Attributes", None)
			if ia2:
				cls = ia2.get("class", "")
				if "fd365im1" in cls:
					self._composer_cache = obj
					try: self._message_list_cache = obj.parent.parent.parent.parent.parent.previous.lastChild.lastChild
					except: pass
				elif "focusable-list-item" in cls:
					if not self._message_list_cache: self._message_list_cache = obj.parent
			if not self._chats_cache and obj.role == controlTypes.Role.LIST:
				loc = obj.location
				if loc and loc.left < 450 and loc.width < 500: self._chats_cache = obj
			if obj.name and re.search(r'^(Chats|Chat|Daftar chat)$', obj.name, re.I):
				try: self._chats_cache = obj.parent.parent.next.firstChild
				except: pass
			if obj.name and config.conf.get("WhatsAppEnhancer", {}).get("filter_phone_numbers", True):
				obj.name = re.sub(r'\+\d[()\d\s\u202c-]{12,}', '', obj.name)
		except:
			pass

	def event_gainFocus(self, obj, nextHandler):
		if not self.mainWindow or not self.mainWindow.windowHandle:
			curr = obj
			while curr:
				if curr.role == controlTypes.Role.WINDOW:
					self.mainWindow = curr
					break
				curr = curr.parent
		if not config.conf.get("WhatsAppEnhancer", {}).get("disable_browse_mode_lock", False):
			if obj.treeInterceptor: obj.treeInterceptor.passThrough = True
		nextHandler()

	def terminate(self):
		self._unpatch_speech()
		super().terminate()

	def _patch_speech(self):
		try:
			self._original_speak = speech.speech.speak
			speech.speech.speak = self._on_speak
		except:
			self._original_speak = speech.speak
			speech.speak = self._on_speak

	def _unpatch_speech(self):
		if self._original_speak:
			try: self.speech.speak = self._original_speak
			except: speech.speak = self._original_speak

	def _on_speak(self, sequence, *args, **kwargs):
		new_sequence = []
		hp = r"(For more options|Untuk opsi|Para lebih|Para más|Pour plus|Per lebih|Per lebih banyak|Per lebih lanjut|Per più|Für weitere|Para mais|Daha fazla|Voor meer|Untuk mengakses|Untuk selengkapnya|Untuk bantuan|Untuk mendapatkan|Для получения|Để biết thêm|สำหรับตัวเลือก|その他のオプション|更多选项|अधिक विकल्पों|추가 옵션)"
		for item in sequence:
			if isinstance(item, str) and not config.conf.get("WhatsAppEnhancer", {}).get("read_usage_hints", True):
				if re.search(r"(arrow|panah|flecha|flèche|freccia|ok|Ok|стрелк|menu|konteks|context|contexto|contextuel|contestuale|Kontext|Bağlam)", item, re.I) and re.search(hp, item, re.I):
					item = re.sub(hp + r".*", "", item, flags=re.I).strip()
			new_sequence.append(item)
		if self._original_speak: self._original_speak(new_sequence, *args, **kwargs)
		if not self._is_reviewing:
			text_list = [item for item in new_sequence if isinstance(item, str)]
			full_text = " ".join(text_list)
			if full_text.strip():
				self._last_spoken_text = full_text
				self._last_spoken_lines = [line for line in text_list if line.strip()]
				self._review_cursor = 0
				self._review_line_index = 0

	@script(description=_("Review previous character"), gesture="kb:NVDA+leftArrow")
	def script_review_previous_character(self, gesture):
		if not self._last_spoken_text: return
		self._is_reviewing = True
		try:
			if self._review_cursor > 0:
				self._review_cursor -= 1
			
			if self._review_cursor >= len(self._last_spoken_text):
				self._review_cursor = len(self._last_spoken_text) - 1
				
			speech.speak([self._last_spoken_text[self._review_cursor]])
		finally: self._is_reviewing = False

	@script(description=_("Review next character"), gesture="kb:NVDA+rightArrow")
	def script_review_next_character(self, gesture):
		if not self._last_spoken_text: return
		self._is_reviewing = True
		try:
			if self._review_cursor < len(self._last_spoken_text) - 1:
				self._review_cursor += 1
			elif self._review_cursor >= len(self._last_spoken_text):
				self._review_cursor = len(self._last_spoken_text) - 1
			speech.speak([self._last_spoken_text[self._review_cursor]])
		finally: self._is_reviewing = False

	@script(description=_("Review previous word"), gesture="kb:NVDA+control+leftArrow")
	def script_review_previous_word(self, gesture):
		if not self._last_spoken_text: return
		self._is_reviewing = True
		try:
			cur = self._review_cursor - 1
			while cur >= 0 and self._last_spoken_text[cur].isspace(): cur -= 1
			word_end = cur + 1
			while cur >= 0 and not self._last_spoken_text[cur].isspace(): cur -= 1
			self._review_cursor = max(0, cur + 1)
			speech.speak([self._last_spoken_text[self._review_cursor:word_end]])
		finally: self._is_reviewing = False

	@script(description=_("Review next word"), gesture="kb:NVDA+control+rightArrow")
	def script_review_next_word(self, gesture):
		if not self._last_spoken_text: return
		self._is_reviewing = True
		try:
			cur = self._review_cursor
			while cur < len(self._last_spoken_text) and not self._last_spoken_text[cur].isspace(): cur += 1
			while cur < len(self._last_spoken_text) and self._last_spoken_text[cur].isspace(): cur += 1
			self._review_cursor = cur
			word_end = cur
			while word_end < len(self._last_spoken_text) and not self._last_spoken_text[word_end].isspace(): word_end += 1
			speech.speak([self._last_spoken_text[self._review_cursor:word_end]])
		finally: self._is_reviewing = False

	@script(description=_("Review previous line"), gesture="kb:NVDA+upArrow")
	def script_review_previous_line(self, gesture):
		if not self._last_spoken_lines: return
		self._is_reviewing = True
		try:
			if self._review_line_index > 0: self._review_line_index -= 1
			speech.speak([self._last_spoken_lines[self._review_line_index]])
		finally: self._is_reviewing = False

	@script(description=_("Review next line"), gesture="kb:NVDA+downArrow")
	def script_review_next_line(self, gesture):
		if not self._last_spoken_lines: return
		self._is_reviewing = True
		try:
			if self._review_line_index < len(self._last_spoken_lines) - 1: self._review_line_index += 1
			speech.speak([self._last_spoken_lines[self._review_line_index]])
		finally: self._is_reviewing = False

	@script(description=_("Inspector"), gesture="kb:NVDA+shift+i")
	def script_inspector(self, gesture):
		obj = api.getFocusObject()
		loc = obj.location
		loc_str = f"L:{loc.left}, T:{loc.top}, W:{loc.width}, H:{loc.height}" if loc else "No Loc"
		auto_id = getattr(obj, "UIAAutomationId", "None")
		ui.message(f"Role: {obj.role}, {loc_str}, Name: '{obj.name}', ID: {auto_id}")

	@script(description=_("Read title"), gesture="kb:alt+t")
	def script_read_profile_name(self, gesture):
		from scriptHandler import getLastScriptRepeatCount
		if getLastScriptRepeatCount() == 1:
			state = "enabled" if TitleObserver.toggle(self) else "disabled"
			ui.message(f"Chat activity tracking {state}")
			return
		el = getattr(self, "get_title_element", lambda: None)()
		if el: ui.message(", ".join([c.name for c in el.children if c.name]))

	@script(description=_("Toggle live chat"), gesture="kb:alt+l")
	def script_toggle_live_chat(self, gesture):
		state = "enabled" if ChatObserver.toggle(self) else "disabled"
		ui.message(f"Automatic new message reading {state}")

	@script(description=_("Dedicated text window"), gesture="kb:alt+c")
	def script_show_text_message(self, gesture):
		obj = api.getFocusObject()
		if obj.name: TextWindow(obj.name.strip(), "Message Text", readOnly=False)
		else: gesture.send()

	@script(description=_("Copy message"), gesture="kb:control+c")
	def script_copyMessage(self, gesture):
		obj = api.getFocusObject()
		if obj.role == controlTypes.Role.LISTITEM and obj.name:
			api.copyToClip(obj.name.strip())
			ui.message("Copied")
		else: gesture.send()

	@script(description=_("Context menu"), gesture="kb:shift+enter")
	def script_contextMenu(self, gesture):
		f = api.getFocusObject()
		if f.role == controlTypes.Role.EDITABLETEXT:
			gesture.send()
			return
		p = r"(Context|konteks|contexto|contextuel|contestuale|Kontext|Bağlam|السياق|ngữ cảnh|บริบท|コンテキスト|上下文|संदर्भ|컨텍스트|Контекстное)"
		res = find_button_by_name(f, p)
		if not res and f.parent: res = find_button_by_name(f.parent, p)
		if res: res[0].doAction()

	@script(description=_("Play voice message"), gesture="kb:enter")
	def script_playVoiceMessage(self, gesture):
		f = api.getFocusObject()
		if f.role == controlTypes.Role.EDITABLETEXT:
			gesture.send()
			return
		p = r"(Play|Putar|Reproducir|Lire|Riproduci|Reproduzir|abspielen|çal|afspelen|Odtwórz|تشغيل|Phát|เล่น|再生|播放|चलाएं|재생|Воспроизвести)"
		res = find_button_by_name(f, p)
		if res: res[0].doAction()
		else: gesture.send()

	@script(description=_("Voice call"), gesture="kb:shift+alt+c")
	def script_call(self, gesture): perform_voice_call(self)

	@script(description=_("Video call"), gesture="kb:shift+alt+v")
	def script_videoCall(self, gesture): perform_video_call(self)

	@script(description=_("Next object"), gesture="kb:control+]")
	def script_nextObject(self, gesture):
		s = getattr(globalCommands.commands, "script_nextObject", getattr(globalCommands.commands, "script_next", None))
		if s: s(gesture)
		else: gesture.send()

	@script(description=_("Previous object"), gesture="kb:control+[")
	def script_previousObject(self, gesture):
		s = getattr(globalCommands.commands, "script_previousObject", getattr(globalCommands.commands, "script_previous", None))
		if s: s(gesture)
		else: gesture.send()

	@script(description=_("Toggle browse mode"), gestures=["kb:NVDA+space"])
	def script_disableBrowseModeToggle(self, gesture):
		lock_disabled = False
		try: lock_disabled = bool(config.conf["WhatsAppEnhancer"].get("disable_browse_mode_lock", False))
		except: pass
		if lock_disabled:
			import globalCommands
			s = getattr(globalCommands.commands, "script_toggleVirtualBufferPassThrough", None)
			if s: s(gesture)
			return
		obj = api.getFocusObject()
		ti = getattr(obj, "treeInterceptor", None)
		if ti:
			ti.passThrough = True
			ui.message(_("Browse Mode is disabled for WhatsApp"))
		else: gesture.send()
