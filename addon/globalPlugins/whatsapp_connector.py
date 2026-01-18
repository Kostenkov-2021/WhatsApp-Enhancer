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

	def onSave(self):
		config.conf["WhatsAppEnhancer"]["filter_phone_numbers"] = self.filter_phone_numbers.IsChecked()

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