import globalPluginHandler
import appModuleHandler
import addonHandler
import config
import gui
import wx
from gui.settingsDialogs import SettingsPanel, NVDASettingsDialog
import languageHandler

addonHandler.initTranslation()

SPEC = {
	'automaticReadingOfNewMessages': 'boolean(default=False)',
	'filter_phone_numbers': 'boolean(default=True)',
	'read_usage_hints': 'boolean(default=True)',
	'disable_browse_mode_lock': 'boolean(default=False)',
}

class WhatsAppEnhancerSettings(SettingsPanel):
	title = _("WhatsApp Enhancer")

	def makeSettings(self, settingsSizer):
		settingsSizerHelper = gui.guiHelper.BoxSizerHelper(self, sizer=settingsSizer)
		
		# Phone Number Filter
		self.filter_phone_numbers = settingsSizerHelper.addItem(
			wx.CheckBox(self, label=_("Filter phone numbers in chat headers"))
		)
		self.filter_phone_numbers.SetValue(config.conf["WhatsAppEnhancer"]["filter_phone_numbers"])

		# Usage Hints
		self.read_usage_hints = settingsSizerHelper.addItem(
			wx.CheckBox(self, label=_("Read usage hints while navigating chat list"))
		)
		self.read_usage_hints.SetValue(config.conf["WhatsAppEnhancer"]["read_usage_hints"])

		self.disable_browse_mode_lock = settingsSizerHelper.addItem(
			wx.CheckBox(self, label=_("Disable browse mode lock (not recommended)"))
		)
		self.disable_browse_mode_lock.SetValue(config.conf["WhatsAppEnhancer"]["disable_browse_mode_lock"])

	def onSave(self):
		config.conf["WhatsAppEnhancer"]["filter_phone_numbers"] = self.filter_phone_numbers.IsChecked()
		config.conf["WhatsAppEnhancer"]["read_usage_hints"] = self.read_usage_hints.IsChecked()
		config.conf["WhatsAppEnhancer"]["disable_browse_mode_lock"] = self.disable_browse_mode_lock.IsChecked()
		config.conf.save()

class GlobalPlugin(globalPluginHandler.GlobalPlugin):
	def __init__(self):
		super(GlobalPlugin, self).__init__()
		
		# Register Config Spec
		config.conf.spec['WhatsAppEnhancer'] = SPEC
		
		# Register the app module for both common WhatsApp executable names
		appModuleHandler.registerExecutableWithAppModule("WhatsApp", "whatsapp_root")
		appModuleHandler.registerExecutableWithAppModule("WhatsApp.Root", "whatsapp_root")
		
		# Register Settings Panel
		NVDASettingsDialog.categoryClasses.append(WhatsAppEnhancerSettings)

	def terminate(self):
		super(GlobalPlugin, self).terminate()
		appModuleHandler.unregisterExecutable("WhatsApp")
		appModuleHandler.unregisterExecutable("WhatsApp.Root")
		
		# Unregister Settings Panel
		if WhatsAppEnhancerSettings in NVDASettingsDialog.categoryClasses:
			NVDASettingsDialog.categoryClasses.remove(WhatsAppEnhancerSettings)