
import ui
import api
import controlTypes
from .wh_utils import collect_elements, find_button_by_name, find_by_name
import re

# Button search patterns (supports English and Indonesian)
PATTERN_CHATS = r"^(Chats|Chat|Daftar chat)$"
PATTERN_VOICE_CALL = r"(Voice call|Panggilan suara)"
PATTERN_VIDEO_CALL = r"(Video call|Panggilan video)"

def focus_chats(app_instance):
	"""
	Focuses on the chat list.
	Strategy 1: Search for specific 'Chats' button.
	Strategy 2: Fallback to the leftmost list object.
	"""
	root = app_instance.mainWindow
	if not root:
		ui.message("Main window not found")
		return

	# Strategy 1: Search for specific button
	buttons = find_button_by_name(root, PATTERN_CHATS)
	if buttons:
		buttons[0].setFocus()
		return

	# Strategy 2: Fallback to leftmost LIST object
	def is_list_candidate(o):
		return o.role == controlTypes.Role.LIST or o.role == 86 # 86 = List role in some UIA versions

	candidates = collect_elements(root, is_list_candidate)
	valid_candidates = [c for c in candidates if c.location and c.location.width > 0]

	if valid_candidates:
		# Sort by left position (smallest = leftmost)
		target = sorted(valid_candidates, key=lambda c: c.location.left)[0]
		target.setFocus()
		if target.firstChild:
			target.firstChild.setFocus()
	else:
		ui.message("Chat list not found")

def focus_messages(app_instance):
	"""
	Focuses on the message list by searching for the widest Document or Grouping area.
	"""
	root = app_instance.mainWindow
	if not root: return

	def is_area_candidate(o):
		return o.role == controlTypes.Role.DOCUMENT or o.role == controlTypes.Role.GROUPING

	candidates = collect_elements(root, is_area_candidate)
	# Filter for areas wider than 300px
	valid_candidates = [c for c in candidates if c.location and c.location.width > 300]

	if valid_candidates:
		# Select the widest one
		target = sorted(valid_candidates, key=lambda c: c.location.width, reverse=True)[0]
		target.setFocus()
	else:
		ui.message("Message list not found")

def focus_composer(app_instance):
	"""
	Focuses on the message composer by searching for the bottommost EditableText.
	"""
	root = app_instance.mainWindow
	if not root: return

	def is_edit_candidate(o):
		return o.role == controlTypes.Role.EDITABLETEXT

	candidates = collect_elements(root, is_edit_candidate)
	valid_candidates = [c for c in candidates if c.location and c.location.height > 0]

	if valid_candidates:
		# Select the bottommost one (largest top coordinate)
		target = sorted(valid_candidates, key=lambda c: c.location.top, reverse=True)[0]
		target.setFocus()
	else:
		ui.message("Composer not found")

def perform_voice_call(app_instance):
	"""Clicks the Voice Call button."""
	root = app_instance.mainWindow or api.getForegroundObject()
	
	buttons = find_button_by_name(root, PATTERN_VOICE_CALL)
	if buttons:
		buttons[0].doAction()
		ui.message("Calling...")
	else:
		ui.message("Voice call button not found")

def perform_video_call(app_instance):
	"""Clicks the Video Call button."""
	root = app_instance.mainWindow or api.getForegroundObject()
	
	buttons = find_button_by_name(root, PATTERN_VIDEO_CALL)
	if buttons:
		buttons[0].doAction()
		ui.message("Video calling...")
	else:
		ui.message("Video call button not found")
