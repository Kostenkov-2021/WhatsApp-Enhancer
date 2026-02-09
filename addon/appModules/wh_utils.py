
import api
import controlTypes
import UIAHandler
from collections import deque
import re

def get_uia_element(obj):
	try: return getattr(obj, "UIAElement", None)
	except: return None

def collect_elements(root, condition, max_items=50):
	if not root: return []
	results = []
	queue = deque([root])
	visited = 0
	while queue and visited < max_items:
		obj = queue.popleft()
		visited += 1
		try:
			if condition(obj): results.append(obj)
			child = obj.firstChild
			while child:
				queue.append(child)
				child = child.next
		except: continue
	return results

def find_by_automation_id(root, auto_id):
	uia = get_uia_element(root)
	if uia:
		try:
			cond = UIAHandler.handler.clientObject.CreatePropertyCondition(UIAHandler.UIA_AutomationIdPropertyId, auto_id)
			els = uia.FindAll(UIAHandler.TreeScope_Descendants, cond)
			from NVDAObjects.UIA import UIA
			return [UIA(UIAElement=els.GetElement(i)) for i in range(els.Length)]
		except: pass
	return []

def find_elements_by_role(root, role):
	uia = get_uia_element(root)
	if uia:
		try:
			import UIAHandler
			m = {
				controlTypes.Role.LIST: UIAHandler.UIA_ListControlTypeId,
				controlTypes.Role.EDITABLETEXT: UIAHandler.UIA_EditControlTypeId,
				controlTypes.Role.DOCUMENT: UIAHandler.UIA_DocumentControlTypeId,
				controlTypes.Role.GROUPING: UIAHandler.UIA_GroupControlTypeId,
				controlTypes.Role.BUTTON: UIAHandler.UIA_ButtonControlTypeId,
			}
			t = m.get(role)
			if t:
				cond = UIAHandler.handler.clientObject.CreatePropertyCondition(UIAHandler.UIA_ControlTypePropertyId, t)
				els = uia.FindAll(UIAHandler.TreeScope_Descendants, cond)
				from NVDAObjects.UIA import UIA
				return [UIA(UIAElement=els.GetElement(i)) for i in range(els.Length)]
		except: pass
	return collect_elements(root, lambda o: o.role == role)

def find_button_by_name(root, pattern):
	uia = get_uia_element(root)
	reg = re.compile(pattern, re.I)
	if uia:
		try:
			cond = UIAHandler.handler.clientObject.CreatePropertyCondition(UIAHandler.UIA_ControlTypePropertyId, UIAHandler.UIA_ButtonControlTypeId)
			els = uia.FindAll(UIAHandler.TreeScope_Descendants, cond)
			from NVDAObjects.UIA import UIA
			res = []
			for i in range(els.Length):
				e = els.GetElement(i)
				if reg.search(e.CurrentName or ""): res.append(UIA(UIAElement=e))
			if res: return res
		except: pass
	return collect_elements(root, lambda o: o.role == controlTypes.Role.BUTTON and o.name and reg.search(o.name))
