#!/usr/bin/env python

from gnomevfs import get_local_path_from_uri
from gc import collect
import os.path

import gtk
import gtk.gdk
import gnome.ui
import gobject
import os
import gtk.glade
import pango

def bytes_to_string(size):
	"""Return a number in a easier way to read"""

	giga = 1024 * 1024 * 1024
	mega = 1024 * 1024
	kilo = 1024

	if size >= giga:
		str = "%.2f GiB" % (float(size) / float(giga))
	elif size >= mega:
		str = "%.2f MiB" % (float(size) / float(mega))
	elif size >= kilo:
		str = "%.2f KiB" % (float(size) / float(kilo))
	else:
		str = "%d bytes" % size

	return str


class ThumbnailChecker:
	OK = 0
	EXTERNAL = 1
	ORPHAN = 2
	NON_FD = 3
	INVALID = 4

	def __init__(self):
		self.id = None
		self.first_time = True

		xml = gtk.glade.XML('thumbnail-checker.glade', None, None)
		self.model = gtk.TreeStore(str, str, str)

		self.window = xml.get_widget('window')
		self.treeview = xml.get_widget('treeview')
		self.progressbar = xml.get_widget('progressbar')
		self.progress = xml.get_widget('progress')
		self.button_delete = xml.get_widget('button_delete')
		self.button_start = xml.get_widget('button_start')
		self.button_stop = xml.get_widget('button_stop')
		xml.signal_autoconnect(self)

		self.treeview.set_search_column(1)
		self.treeview.set_model(self.model)
		selection = self.treeview.get_selection()
		selection.set_mode(gtk.SELECTION_MULTIPLE)
		selection.connect("changed", self.on_selection_changed)

		renderer = gtk.CellRendererText()
		renderer.set_property("ellipsize", pango.ELLIPSIZE_MIDDLE)
		column = gtk.TreeViewColumn("File name or Thumbnail file", 
		                            renderer, text=0)
		column.set_resizable(True)
		column.set_expand(True)
		self.treeview.append_column(column)

		renderer = gtk.CellRendererText()
		renderer.set_property('xalign', 1.0)
		column = gtk.TreeViewColumn("Size", renderer, text=1)
		column.set_resizable(True)
		column.set_min_width(80)
		column.set_resizable(True)
		self.treeview.append_column(column)

	def show(self):
		self.window.show_all()

	def on_quit(self, *args):
		gtk.main_quit()

	def on_button_delete_clicked(self, button, *args):
		selection = self.treeview.get_selection()
		model, paths = selection.get_selected_rows()
		refs = []
		for path in paths:
			refs.append(gtk.TreeRowReference(model, path))

		for ref in refs:
			path = ref.get_path()
			iter = model.get_iter(path)
			filename = model.get(iter, 2)[0]
			os.unlink(os.path.expanduser(filename))
			model.remove(iter)

	def on_button_stop_clicked(self, button, *args):
		gobject.source_remove(self.id)
		self.button_stop.set_sensitive(False)
		self.button_start.set_sensitive(True)

	def on_button_start_clicked(self, button, *args):
		self.button_stop.set_sensitive(True)
		self.button_start.set_sensitive(False)
		if self.first_time:
			self.first_time = False
			self.task = self.walk()
		self.id = gobject.idle_add(self.task.next)

	def walk(self, *args):
		(self.invalid_size, self.invalid_count) = (0, 0)
		(self.non_fd_size, self.non_fd_count) = (0, 0)
		(self.orphan_size, self.orphan_count) = (0, 0)
		(self.external_size, self.external_count) = (0, 0)
		
		self.orphan_iter = self.model.append(None, ["Orphans", '0', None])
		self.external_iter = self.model.append(None,
                                  ["Orphans and/or Externals", '0', None])
		self.invalid_iter = self.model.append(None,
                                  ["Invalid (broken image)", '0', None])
		self.non_fd_iter = self.model.append(None,
                                  ["No Free Desktop compliant", '0', None])

		homedir = os.path.expanduser('~')
		rootdir = os.path.join(homedir, '.thumbnails')
		for root, dirs, files in os.walk(rootdir):
			i = 0.0

			text = "%d of %d" % (0, len(files))
			self.progressbar.set_text(text)
			text = "Processing %s ..." % root
			self.progress.set_text(text)

			for name in files:
				i = i + 1.0
				uri = None
				filename = os.path.join(root, name)

				self.progressbar.set_fraction(i / len(files))
				self.progressbar.set_text(text)

				(result, resource) = self.verify_thumbnail(filename)
				if resource.startswith(homedir):
					resource = resource.replace(homedir, '~')

				if result == self.EXTERNAL:
					self.compute(filename, 'external', resource, 
					             "Orphans and/or Externals [%d]")
				elif result == self.ORPHAN:
					self.compute(filename, 'orphan', resource,
					             "Orphans [%d]")
				elif result == self.NON_FD:
					self.compute(filename, 'non_fd', resource, 
					             "No Free Desktop compliant [%d]")
				elif result == self.INVALID:
					self.compute(filename, 'invalid', resource, 
					             "Invalid (broken images) [%d]")

				collect()
				yield True
				
			text = "%s done.  Trying the next one..." % root
			self.progress.set_text(text)
			yield True
			
		self.walk_done()
		yield False

	#def delete_selected_thumbnail(self, treemodel, path, iter):
	#	file = treemodel.get(iter, 2)[0]
	#	os.unlink(os.path.expanduser(file))
	def walk_done(self):
		gobject.source_remove(self.id)
		self.progressbar.set_text('Done')
		self.progress.set_text('')
		self.button_stop.set_sensitive(False)

	def on_selection_changed(self, selection):
		has_selection = (selection.count_selected_rows () != 0)
		self.button_delete.set_sensitive(has_selection)
	
	def verify_thumbnail(self, filename):
		try:
			pixbuf = gtk.gdk.pixbuf_new_from_file(filename)
			uri = pixbuf.get_option('tEXt::Thumb::URI')
		except:
			# Broken thumbnail
			uri = ''

		try:
			path = get_local_path_from_uri(uri)
		except:
			# External resource or invalid uri
			path = ''

		if len(path) == 0 and uri is not None and len(uri):
			return (self.EXTERNAL, uri)
		if len(path) and not os.path.lexists(path):
			return (self.ORPHAN, filename)
		if uri is None:
			return (self.NON_FD, filename)
		if len(uri) == 0:
			return (self.INVALID, filename)
		return (self.OK, filename)

	def compute(self, filename, item, element, text):
		sum_size = getattr(self, item + '_size')
		counter  = getattr(self, item + '_count')
		iter = getattr(self, item + '_iter')
		
		size = os.path.getsize(filename)
		sum_size += size
		counter += 1

		setattr(self, item + '_size', sum_size)
		setattr(self, item + '_count', counter)

		str_size = bytes_to_string(size)
		self.model.append(iter, [element, str_size, filename])

		str_size = bytes_to_string(sum_size)
		self.model.set(iter, 1, str_size)
		self.model.set(iter, 0, text % counter)
	
if __name__ == "__main__":
	checker = ThumbnailChecker()
	checker.show()

	gtk.main()
