#!/usr/bin/env python

import pygtk
pygtk.require("2.0")
import gtk
import sys
import wave
import audioop
import array
import cairo
import math
import itertools

class Base:
	ui ='''<ui>
		<menubar name="mainmenu">
			<menu action="File">
				<menuitem action="New"/>
				<menuitem action="Open"/>
				<menuitem action="Save"/>
				<menuitem action="Save as"/>
				<separator/>
				<menuitem action="Quit"/>
			</menu>
			<menu action="View">
				<menuitem action="Zoom in"/>
				<menuitem action="Zoom out"/>
				<menuitem action="Fit to window"/>
			</menu>
			<menu action="Options">
			</menu>
			<menu action="Help">
				<menuitem action="About"/>
			</menu>
		</menubar>
		<toolbar name="toolbar">
			<toolitem action="Quit"/>
			<separator/>
			<toolitem action="Zoom in"/>
			<toolitem action="Zoom out"/>
			<toolitem action="Fit to window"/>
		</toolbar>
	</ui>'''

	def __init__(self):
		self.setupwindow()
		self.openwavfile("out.wav") # TODO: remove this line

	def setupwindow(self):
		# window itself
		window = gtk.Window()
		self.window = window
		window.connect("delete_event",
				lambda widget, event, data=None: not self.confirmquit())
		window.connect("destroy", lambda w: gtk.main_quit())
		window.set_default_size(400, 300)
		window.set_title("Subtitle")

		vbox = gtk.VBox()
		window.add(vbox)
		vbox.show()

		# menu
		uimanager = gtk.UIManager()
		accelgroup = uimanager.get_accel_group()
		window.add_accel_group(accelgroup)
		actiongroup = gtk.ActionGroup("actiongroup")
		self.actiongroup = actiongroup
		actiongroup.add_actions([
					("File", None, "_File"),
					("Options", None, "_Options"),
					("View", None, "_View"),
					("Help", None, "_Help"),
					("New", gtk.STOCK_NEW, None, None, None, self.action_new),
					("Open", gtk.STOCK_OPEN, None, None, None, 
						self.action_open),
					("Save", gtk.STOCK_SAVE, None, None, None, 
						self.action_save),
					("Save as", gtk.STOCK_SAVE_AS, None, None, None, 
						self.action_saveas),
					("Quit", gtk.STOCK_QUIT, None, None, None, 
						self.action_quit),
					("Zoom in", gtk.STOCK_ZOOM_IN, None, None, None, 
						self.action_zoomin),
					("Zoom out", gtk.STOCK_ZOOM_OUT, None, None, None, 
						self.action_zoomout),
					("Fit to window", gtk.STOCK_ZOOM_FIT, None, None, None, 
						self.action_fittowindow),
					("About", gtk.STOCK_ABOUT, None, None, None, 
						self.action_about),
					])
		uimanager.insert_action_group(actiongroup, 0)
		uimanager.add_ui_from_string(self.ui)

		# main box
		self.mainbox = gtk.VBox()
		self.mainbox.show()
		vbox.pack_start(uimanager.get_widget("/mainmenu"), False)
		vbox.pack_start(uimanager.get_widget("/toolbar"), False)
		vbox.pack_start(self.mainbox, True)

		window.show()

	def confirmquit(self):
		"""
		if no unsaved changes return True (go ahead and quit)
		if unsaved changes confirm with the user and return True if we should 
		quit, otherwise False
		"""
		if not self.has_unsaved_changes():
			return True
		dialog = gtk.MessageDialog(self.window, gtk.DIALOG_DESTROY_WITH_PARENT, 
				gtk.MESSAGE_QUESTION, gtk.BUTTONS_YES_NO,
				"There are unsaved changes. Are you sure you want to quit?")
		response = dialog.run()
		dialog.destroy()
		return response == gtk.RESPONSE_YES

	def has_unsaved_changes(self):
		# TODO
		return False

	def action_quit(self, widget, data=None):
		if self.confirmquit():
			gtk.main_quit()

	def action_new(self, widget, data=None):
		# TODO
		print "new"

	def action_open(self, widget, data=None):
		chooser = gtk.FileChooserDialog(
				title="Open...",
				action=gtk.FILE_CHOOSER_ACTION_OPEN,
				buttons=(
					gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
					gtk.STOCK_OPEN, gtk.RESPONSE_OK,
					),
				)
		chooser.set_default_response(gtk.RESPONSE_OK)

		filefilter = gtk.FileFilter()
		filefilter.set_name("Wave files")
		filefilter.add_pattern("*.wav")
		filefilter.add_pattern("*.wav")
		filefilter.add_mime_type("audio/wave")
		filefilter.add_mime_type("audio/wav")
		filefilter.add_mime_type("audio/x-wav")
		filefilter.add_mime_type("audio/vnd.wave")
		chooser.add_filter(filefilter)

		filefilter = gtk.FileFilter()
		filefilter.set_name("All files")
		filefilter.add_pattern("*")
		chooser.add_filter(filefilter)

		filename = None
		response = chooser.run()
		if response == gtk.RESPONSE_OK:
			filename = chooser.get_filename()
		chooser.destroy()

		self.openwavfile(filename)

	def action_save(self, widget, data=None):
		# TODO
		print "save"

	def action_saveas(self, widget, data=None):
		# TODO
		print "saveas"

	def action_zoomin(self, widget, data=None):
		self.waveformarea.zoomin()

	def action_zoomout(self, widget, data=None):
		self.waveformarea.zoomout()

	def action_fittowindow(self, widget, data=None):
		self.waveformarea.fittowindow()

	def action_about(self, widget, data=None):
		dialog = gtk.MessageDialog(self.window, gtk.DIALOG_DESTROY_WITH_PARENT, 
				gtk.MESSAGE_INFO, gtk.BUTTONS_CLOSE,
				"py-subtitle, by Bart Nagel <bart@tremby.net>")
		dialog.run()
		dialog.destroy()

	def openwavfile(self, filename):
		# open wave file
		try:
			infile = wave.open(filename, "r")
		except wave.Error as e:
			dialog = gtk.MessageDialog(self.window, 
					gtk.DIALOG_DESTROY_WITH_PARENT, gtk.MESSAGE_ERROR, 
					gtk.BUTTONS_CLOSE, "Error: %s" % e)
			dialog.run()
			dialog.destroy()
			return

		# get raw frame data (binary string of integers)
		frames = infile.readframes(infile.getnframes())

		# mix down to mono if it's stereo
		if infile.getnchannels() > 1:
			frames = audioop.tomono(frames, infile.getsampwidth(), 0.5, 0.5)

		# get list of integer samples
		samples = binary_unsigned_integers_to_list(frames, 
				infile.getsampwidth())

		# trigger the waveform setup etc
		self.newaudio(Audio(samples, infile.getframerate(), 
			infile.getsampwidth(), filename))

	def newaudio(self, audio):
		self.audio = audio

		self.empty_mainbox()

		entry = gtk.Label("audio's length is %f seconds" % audio.get_length())
		entry.show()
		self.mainbox.pack_start(entry, False)

		scrollable = gtk.ScrolledWindow()
		scrollable.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_NEVER)
		self.waveformarea = waveformarea = WaveformArea(self.audio)
		waveformarea.show()
		scrollable.add_with_viewport(waveformarea)
		scrollable.show_all()
		self.mainbox.pack_start(scrollable, True)

	def empty_mainbox(self):
		for child in self.mainbox.get_children():
			self.mainbox.remove(child)
			child.destroy()

	def main(self):
		gtk.main()

class WaveformArea(gtk.DrawingArea):
	def __init__(self, audio):
		super(WaveformArea, self).__init__()
		self.connect("expose_event", self.expose)
		self.audio = audio

		self.samplesperpixel = None

	def fittowindow(self):
		"""
		zoom such that the entire waveform can fit in the window at its current 
		size
		"""
		parentrect = self.get_parent().get_allocation()
		self.set_samplesperpixel(math.ceil(float(len(self.audio.get_monosamples())) 
			/ (parentrect.width - 2)))
		self.setsize()

	def zoomin(self, factor=2):
		"""
		zoom in by a certain factor
		"""
		self.set_samplesperpixel(self.get_samplesperpixel() / factor)

	def zoomout(self, factor=2):
		"""
		zoom out by a certain factor
		"""
		self.set_samplesperpixel(self.get_samplesperpixel() * factor)

	def setsize(self):
		"""
		resize the canvas based on the current zoom level and redraw
		"""
		parentrect = self.get_parent().get_allocation()
		width = int(float(len(self.audio.get_monosamples())) / 
				self.get_samplesperpixel())
		self.set_size_request(width, 0)
		self.queue_draw()

	def expose(self, widget, event):
		"""
		expose event callback -- fit to window if there is no zoom level, make 
		cairo context, mask to visible area and call draw method
		"""
		if self.get_samplesperpixel() is None:
			self.fittowindow()

		context = widget.window.cairo_create()

		# set clip area for redraw speed
		context.rectangle(event.area.x, event.area.y, event.area.width, 
				event.area.height)
		context.clip()

		self.draw(context)
		return False

	def get_samplesperpixel(self):
		"""
		get the number of samples per pixel (zoom level)
		"""
		return self.samplesperpixel

	def set_samplesperpixel(self, samplesperpixel):
		"""
		set the number of samples per pixel (zoom level), recalculate the 
		envelope and resize the canvas
		"""
		self.samplesperpixel = int(samplesperpixel)

		# get minimums and maximums for each pixel column of the envelope
		print "make envelope"
		self.envelope = []
		for startsample in range(0, len(self.audio.get_monosamples()), 
				self.get_samplesperpixel()):
			minsample = float("inf")
			maxsample = float("-inf")
			for sample in self.audio.get_monosamples()[startsample:startsample+self.get_samplesperpixel()]:
				minsample = min(minsample, sample)
				maxsample = max(maxsample, sample)
			self.envelope.append((minsample, maxsample))
		print "make envelope done"

		self.setsize()

	def draw(self, context):
		"""
		draw the waveform
		"""
		context.scale(len(self.audio.get_monosamples()) / 
				self.get_samplesperpixel(), self.get_allocation().height)

		# transform context so we can paint samples on as is
		context.save()
		context.translate(0, 0.5)
		context.scale(1.0 / len(self.envelope), self.audio.get_sample_scale() / 2)

		# draw envelope shape
		context.move_to(0, 0)
		for i, minmax in enumerate(self.envelope):
			# draw bottom edge
			context.line_to(i, minmax[0])
		for i, minmax in itertools.izip(xrange(len(self.envelope) - 1, -1, -1), reversed(self.envelope)):
			# draw top edge
			context.line_to(i, minmax[1])
		context.close_path()

		# restore 1x1 context
		context.restore()

		# fill the shape
		context.set_source_rgb(0.6, 0.6, 1.0)
		context.fill()

class Audio:
	def __init__(self, monosamples, samplerate, samplewidth, filename):
		self.monosamples = monosamples
		self.samplerate = samplerate
		self.samplewidth = samplewidth
		self.filename = filename
		self.length = None
	
	def get_monosamples(self):
		return self.monosamples
	def get_samplerate(self):
		return self.samplerate
	def get_samplewidth(self):
		return self.samplewidth
	def get_filename(self):
		return self.filename

	def get_length(self):
		"""
		return the length of the audio in seconds
		"""
		if self.length is None:
			self.length = float(len(self.monosamples)) / float(self.samplerate)
		return self.length

	def get_sample_scale(self):
		"""
		return the number to multiply a sample by to get something in the range 
		-1 to 1
		"""
		return 1.0 / math.pow(2, self.samplewidth * 8 - 1)

def binary_unsigned_integers_to_list(data, samplewidth):
	"""
	take a binary string of signed integers (little-endian) of width 
	'samplewidth' bytes, return an array of integers
	"""
	if samplewidth == 1:
		arraychar = "b"
	elif samplewidth == 2:
		arraychar = "h"
	else:
		arraychar = "l"
	samples = array.array(arraychar)
	samples.fromstring(data)
	#complementmask = (1 << (samplewidth * 8 - 1))
	#for framenum in range(0, len(data) / samplewidth):
	#	sample = 0
	#	for bytenum in range(0, samplewidth):
	#		sample = sample + (ord(data[framenum * samplewidth + bytenum]) << (8 * bytenum))
	#	if sample & complementmask:
	#		sample = sample - 2 * complementmask
	#	samples.append(sample)

	return samples

if __name__ == "__main__":
	base = Base()
	base.main()
