
import api
import controlTypes
import UIAHandler
from collections import deque
import re

def get_uia_element(obj):
	"""Helper to get the underlying UIA element from an NVDAObject."""
	try:
		return getattr(obj, "UIAElement", None)
	except:
		return None

def collect_elements(root, condition, max_items=5000):
	"""
	Fallback manual collection using BFS.
	Still kept for non-UIA objects or complex conditions.
	"""
	if not root:
		return []

	results = []
	queue = deque([root])
	visited = 0

	while queue and visited < max_items:
		obj = queue.popleft()
		visited += 1

		try:
			if condition(obj):
				results.append(obj)
			
			child = obj.firstChild
			while child:
				queue.append(child)
				child = child.next
		except:
			continue
	
	return results

def find_by_automation_id(root, auto_id):
	"""Finds elements by UIAAutomationId using native UIA search for performance."""
	uia_root = get_uia_element(root)
	if uia_root:
		try:
			# Create UIA condition for AutomationId
			condition = UIAHandler.handler.clientObject.CreatePropertyCondition(
				UIAHandler.UIA_AutomationIdPropertyId, auto_id
			)
			# Find all matches natively
			found_elements = uia_root.FindAll(UIAHandler.TreeScope_Descendants, condition)
			# Wrap native elements back into NVDAObjects
			from NVDAObjects.UIA import UIA
			return [UIA(UIAElement=found_elements.GetElement(i)) for i in range(found_elements.Length)]
		except:
			pass
	
	# Fallback if UIA search fails
	return collect_elements(root, lambda o: o.UIAAutomationId == auto_id)

def find_by_name(root, name, partial=False):
	"""Finds elements by Name using native UIA search when possible."""
	uia_root = get_uia_element(root)
	if uia_root and not partial:
		try:
			condition = UIAHandler.handler.clientObject.CreatePropertyCondition(
				UIAHandler.UIA_NamePropertyId, name
			)
			found_elements = uia_root.FindAll(UIAHandler.TreeScope_Descendants, condition)
			from NVDAObjects.UIA import UIA
			return [UIA(UIAElement=found_elements.GetElement(i)) for i in range(found_elements.Length)]
		except:
			pass
	
	# Fallback for partial match or non-UIA
	return collect_elements(root, lambda o: o.name and (name in o.name if partial else o.name == name))

def find_button_by_name(root, name_pattern):
	"""Finds buttons using native UIA filtering for Role, then regex for Name."""
	uia_root = get_uia_element(root)
	if uia_root:
		try:
			# Native UIA filter for Button control type
			condition = UIAHandler.handler.clientObject.CreatePropertyCondition(
				UIAHandler.UIA_ControlTypePropertyId, UIAHandler.UIA_ButtonControlTypeId
			)
			found_elements = uia_root.FindAll(UIAHandler.TreeScope_Descendants, condition)
			
			from NVDAObjects.UIA import UIA
			regex = re.compile(name_pattern, re.IGNORECASE)
			results = []
			for i in range(found_elements.Length):
				el = found_elements.GetElement(i)
				if regex.search(el.CurrentName or ""):
					results.append(UIA(UIAElement=el))
			return results
		except:
			pass

	# Fallback
	def condition(o):
		if o.role != controlTypes.Role.BUTTON:
			return False
		return o.name and re.search(name_pattern, o.name, re.IGNORECASE)
	
	return collect_elements(root, condition)
