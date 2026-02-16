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
from .wh_observers import ProgressObserver
from .wh_navigation import (
	set_focus_and_navigator
)
from NVDAObjects.IAccessible.ia2Web import Ia2Web
from .wh_utils import find_by_automation_id, find_button_by_name, collect_elements

class CallMenuDialog(Ia2Web):
	_v_idx = -1
	_items_cache = None

	def _get_items(self):
		if self._items_cache: return self._items_cache
		items = []
		stack = [self]
		visited = 0
		while stack and visited < 200:
			o = stack.pop()
			visited += 1
			if o != self:
				is_item = o.role in (controlTypes.Role.BUTTON, controlTypes.Role.LISTITEM)
				cls = getattr(o, "IA2Attributes", {}).get("class", "")
				if "xjb2p0i" in cls or "xk390pu" in cls or "_ahkm" in cls: is_item = True
				
				if is_item:
					name = o.name
					if not name:
						from .wh_utils import collect_elements
						sub = collect_elements(o, lambda x: x.name, max_items=10)
						name = " ".join([s.name for s in sub if s.name])
					if name and name.strip():
						items.append(o)
						continue

			try:
				child = o.lastChild
				while child:
					stack.append(child)
					child = child.previous
			except: pass
		self._items_cache = items
		return self._items_cache

	def _announce(self, items):
		if not items or self._v_idx < 0: return
		obj = items[self._v_idx]
		name = obj.name
		if not name:
			from .wh_utils import collect_elements
			sub = collect_elements(obj, lambda o: o.name, max_items=20)
			name = " ".join([s.name for s in sub if s.name])
		
		state_list = []
		for s_name in ("CHECKED", "SELECTED", "PRESSED", "ON"):
			s_val = getattr(controlTypes.State, s_name, None)
			if s_val and s_val in obj.states:
				state_list.append(controlTypes.stateLabels[s_val])
		
		full_msg = name or _("Option")
		if state_list: full_msg += f" ({', '.join(state_list)})"
		ui.message(full_msg)

	def script_next(self, gesture):
		items = self._get_items()
		if not items: return gesture.send()
		self._v_idx = (self._v_idx + 1) % len(items)
		self._announce(items)

	def script_prev(self, gesture):
		items = self._get_items()
		if not items: return gesture.send()
		self._v_idx = (self._v_idx - 1) % len(items)
		self._announce(items)

	def script_activate(self, gesture):
		items = self._get_items()
		if items and 0 <= self._v_idx < len(items):
			target = items[self._v_idx]
			try: target.doAction()
			except:
				try: target.click()
				except: gesture.send()
		else:
			gesture.send()

	def event_loseFocus(self):
		self._items_cache = None
		self._v_idx = -1

	__gestures = {
		"kb:downArrow": "next",
		"kb:upArrow": "prev",
		"kb:control+enter": "activate",
	}

class HeaderMenuDialog(Ia2Web):
	_v_idx = -1
	_items_cache = None

	def _get_items(self):
		if self._items_cache: return self._items_cache
		root = self
		while root and root.parent and root.role != controlTypes.Role.WINDOW:
			if root.location and root.location.width > 300 and root.location.height > 300: break
			root = root.parent
		
		items = []
		stack = [root]
		visited = 0
		while stack and visited < 300:
			o = stack.pop()
			visited += 1
			if o != root:
				is_target = o.role in (controlTypes.Role.BUTTON, controlTypes.Role.LISTITEM)
				if not is_target and o.role == controlTypes.Role.STATICTEXT and o.name and len(o.name.strip()) > 1:
					is_target = True
				
				if is_target:
					name = o.name
					if not name:
						from .wh_utils import collect_elements
						sub = collect_elements(o, lambda x: x.name, max_items=10)
						name = " ".join([s.name for s in sub if s.name])
					if name and name.strip():
						items.append(o)
						continue

			try:
				child = o.lastChild
				while child:
					stack.append(child)
					child = child.previous
			except: pass
		self._items_cache = items
		return self._items_cache

	def _announce(self, items):
		if not items or self._v_idx < 0: return
		obj = items[self._v_idx]
		name = obj.name
		if not name:
			from .wh_utils import collect_elements
			sub = collect_elements(obj, lambda o: o.name, max_items=20)
			name = " ".join([s.name for s in sub if s.name])
		
		state_list = []
		for s_name in ("CHECKED", "SELECTED", "PRESSED", "ON"):
			s_val = getattr(controlTypes.State, s_name, None)
			if s_val and s_val in obj.states:
				state_list.append(controlTypes.stateLabels[s_val])
		
		full_msg = name or _("Option")
		if state_list: full_msg += f" ({', '.join(state_list)})"
		ui.message(full_msg)

	def script_next(self, gesture):
		items = self._get_items()
		if not items: return gesture.send()
		self._v_idx = (self._v_idx + 1) % len(items)
		self._announce(items)

	def script_prev(self, gesture):
		items = self._get_items()
		if not items: return gesture.send()
		self._v_idx = (self._v_idx - 1) % len(items)
		self._announce(items)

	def script_activate(self, gesture):
		items = self._get_items()
		if items and 0 <= self._v_idx < len(items):
			target = items[self._v_idx]
			try: target.doAction()
			except:
				try: target.click()
				except: gesture.send()
		else:
			gesture.send()

	def event_loseFocus(self):
		self._items_cache = None
		self._v_idx = -1

	__gestures = {
		"kb:downArrow": "next",
		"kb:upArrow": "prev",
		"kb:control+enter": "activate",
	}

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

	def chooseNVDAObjectOverlayClasses(self, obj, clsList):
		cls = getattr(obj, "IA2Attributes", {}).get("class", "")
		if "x1c4vz4f" in cls and "x1nhvcw1" in cls:
			clsList.insert(0, CallMenuDialog)
		if "xyi3aci" in cls and "xe2zdcy" in cls:
			clsList.insert(0, HeaderMenuDialog)
		if "xuwfzo9" in cls and obj.parent:
			p = obj.parent
			p_cls = getattr(p, "IA2Attributes", {}).get("class", "")
			if "xyi3aci" in p_cls:
				clsList.insert(0, HeaderMenuDialog)

	def terminate(self):
		self._unpatch_speech()
		super().terminate()

	def _patch_speech(self):
		try:
			self._original_speak = speech.speech.speak
			speech.speech.speak = self._on_speak
		except:
			self._original_speak = speech.speak

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
		if loc:
			loc_str = _("L:{left}, T:{top}, W:{width}, H:{height}").format(
				left=loc.left, top=loc.top, width=loc.width, height=loc.height
			)
		else:
			loc_str = _("No Loc")
		auto_id = getattr(obj, "UIAAutomationId", "None")
		role_text = controlTypes.roleLabels.get(obj.role, obj.role)
		ui.message(_("Role: {role}, {loc_str}, Name: '{name}', ID: {auto_id}").format(
			role=role_text, loc_str=loc_str, name=obj.name, auto_id=auto_id
		))

	@script(description=_("Dedicated text window"), gesture="kb:alt+c")
	def script_show_text_message(self, gesture):
		obj = api.getFocusObject()
		if obj.name: TextWindow(obj.name.strip(), _("Message Text"), readOnly=False)
		else: gesture.send()

	@script(description=_("Copy message"), gesture="kb:control+c")
	def script_copyMessage(self, gesture):
		obj = api.getFocusObject()
		if obj.role == controlTypes.Role.LISTITEM and obj.name:
			api.copyToClip(obj.name.strip())
			ui.message(_("Copied"))
		else: gesture.send()

	@script(description=_("Context menu"), gesture="kb:shift+enter")
	def script_contextMenu(self, gesture):
		f = api.getFocusObject()
		if f.role == controlTypes.Role.EDITABLETEXT:
			gesture.send()
			return
		
		def is_context_button(obj):
			if obj.role != controlTypes.Role.BUTTON: return False
			cls = getattr(obj, "IA2Attributes", {}).get("class", "")
			return "_ahkm" in cls or ("xhslqc4" in cls and "x16dsc37" in cls)

		from .wh_utils import collect_elements
		curr = f
		for _ in range(8):
			if not curr or curr.role == controlTypes.Role.WINDOW: break
			if is_context_button(curr):
				curr.doAction()
				return
			res = collect_elements(curr, is_context_button, max_items=100)
			if res:
				res[0].doAction()
				return
			curr = curr.parent
		
		gesture.send()

	@script(description=_("Play voice message"), gesture="kb:enter")
	def script_playVoiceMessage(self, gesture):
		f = api.getFocusObject()
		if f.role == controlTypes.Role.EDITABLETEXT:
			gesture.send()
			return
		
		def is_voice_play_button(obj):
			if obj.role != controlTypes.Role.BUTTON: return False
			attrs = getattr(obj, "IA2Attributes", {})
			cls = attrs.get("class", "")
			return "html-button" in cls and "xdj266r" in cls and "x14z9mp" in cls

		if is_voice_play_button(f):
			f.doAction()
			return
		
		from .wh_utils import collect_elements
		res = collect_elements(f, is_voice_play_button, max_items=20)
		if not res and f.parent:
			res = collect_elements(f.parent, is_voice_play_button, max_items=20)
		
		if res:
			res[0].doAction()
		else:
			gesture.send()

	@script(description=_("Open call menu"), gesture="kb:shift+alt+c")
	def script_openCallMenu(self, gesture):
		f = api.getFocusObject()
		if f.role == controlTypes.Role.EDITABLETEXT:
			gesture.send()
			return
		
		if getattr(self, "_call_menu_btn_cache", None) and self._call_menu_btn_cache.windowHandle:
			try:
				self._call_menu_btn_cache.doAction()
				return
			except:
				self._call_menu_btn_cache = None

		def is_call_menu_button(obj):
			if obj.role != controlTypes.Role.BUTTON: return False
			cls = getattr(obj, "IA2Attributes", {}).get("class", "")
			return "xjb2p0i" in cls and "xk390pu" in cls

		from .wh_utils import collect_elements
		root = self.mainWindow or api.getForegroundObject()
		res = collect_elements(root, is_call_menu_button, max_items=500)
		
		if res:
			self._call_menu_btn_cache = res[0]
			res[0].doAction()
		else:
			gesture.send()

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
