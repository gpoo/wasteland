#!/usr/bin/env python

from gnomevfs import get_local_path_from_uri
from gc import collect
from os.path import join, getsize

import gtk
import gtk.gdk
import gnome.ui
import gobject
import os
import gtk.glade
import locale

class ThumbnailChecker:
	def __init__(self):
		self.id = None
		self.first_time = True

		xml = gtk.glade.XML('thumbnail-checker.glade', None, None)
		self.model = gtk.TreeStore(str, str)

		self.window = xml.get_widget('window')
		treeview = xml.get_widget('treeview')
		self.progressbar = xml.get_widget('progressbar')
		self.progress = xml.get_widget('progress')
		self.button_start = xml.get_widget('button_start')
		self.button_stop = xml.get_widget('button_stop')
		xml.signal_autoconnect(self)

		treeview.set_search_column(1)
		treeview.set_model(self.model)

		renderer = gtk.CellRendererText()
		column = gtk.TreeViewColumn("File name or Thumbnail file", renderer, text=0)
		column.set_resizable(True)
		column.set_expand(True)
		treeview.append_column(column)

		renderer = gtk.CellRendererText()
		renderer.set_property('xalign', 1.0)
		column = gtk.TreeViewColumn("Size", renderer, text=1)
		column.set_resizable(True)
		column.set_min_width(80)
		column.set_resizable(True)
		treeview.append_column(column)

	def show(self):
		self.window.show_all()

	def on_quit(self, *args):
		gtk.main_quit()

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
		(invalid_size, invalid_count) = (0, 0)
		(non_fd_size, non_fd_count) = (0, 0)
		(orphan_size, orphan_count) = (0, 0)
		(external_size, external_count) = (0, 0)
		
		orphan_iter = self.model.append(None, ["Orphans", '0'])
		external_iter = self.model.append(None, ["Orphans and/or Externals", '0'])
		invalid_iter = self.model.append(None, ["Invalid (broken image)", '0'])
		non_fd_iter = self.model.append(None, ["No Free Desktop compliant", '0'])

		rootdir = os.path.expanduser('~/.thumbnails')
		homedir = os.path.expanduser('~')
		for root, dirs, files in os.walk(rootdir):
			i = 0.0

			text = "%d of %d" % (0, len(files))
			self.progressbar.set_text(text)
			text = "Processing %s ..." % root
			self.progress.set_text(text)

			for name in files:
				i = i + 1.0
				uri = None
				filename = join(root, name)
				shortname = filename.replace(homedir, '~')

				self.progressbar.set_fraction(i / len(files))
				text = "%d of %d" % (i, len(files))
				self.progressbar.set_text(text)

				try:
					pixbuf = gtk.gdk.pixbuf_new_from_file(filename)
					uri = pixbuf.get_option('tEXt::Thumb::URI')
				except:
					# Broken thumbnail
					uri = ''

				try:
					local_path = get_local_path_from_uri(uri)
				except:
					# External resource or invalid uri
					local_path = ''

				if len(local_path) == 0 and uri is not None and len(uri):
					# external resource (vfs method and/or orphan)
					size = getsize(filename)
					external_size += size
					external_count += 1

					str_size = locale.format("%d", size, grouping=True)
					self.model.append(external_iter, [uri, str_size])

					str_size = locale.format("%d", external_size, grouping=True)
					self.model.set(external_iter, 1, str_size)
					self.model.set(external_iter, 0, 
					               "Orphans and/or Externals [%d]" % external_count)

				elif len(local_path) and not os.path.lexists(local_path):
					# orphan thumbnail
					size = getsize(filename)
					orphan_size += size
					orphan_count += 1
					shortname = local_path.replace(homedir, '~')

					str_size = locale.format("%d", size, grouping=True)
					self.model.append(orphan_iter, [shortname, str_size])

					str_size = locale.format("%d", orphan_size, grouping=True)
					self.model.set(orphan_iter, 1, str_size)
					self.model.set(orphan_iter, 0, "Orphans [%d]" % orphan_count)

				elif uri is None:
					# pixbuf is ok, but no FD compliant.
					size = getsize(filename)
					non_fd_size += size
					non_fd_count += 1

					str_size = locale.format("%d", size, grouping=True)
					self.model.append(non_fd_iter, [shortname, str_size])

					str_size = locale.format("%d", non_fd_size, grouping=True)
					self.model.set(non_fd_iter, 1, str_size)
					self.model.set(non_fd_iter, 0, 
					               "No Free Desktop compliant [%d]" % non_fd_count)

				elif len(uri) == 0:
					# thumbnail is not a valid pixbuf
					size = getsize(filename)
					invalid_size += size
					invalid_count += 1
					shortname = filename.replace(homedir, '~')

					str_size = locale.format("%d", size, grouping=True)
					self.model.append(invalid_iter, [shortname, str_size])

					str_size = locale.format("%d", invalid_size, grouping=True)
					self.model.set(invalid_iter, 1, str_size)
					self.model.set(invalid_iter, 0, 
					               "Invalid (broken images) [%d]" % invalid_count)

				collect()
				yield True

			text = "%s done.  Trying the next one..." % root
			self.progress.set_text(text)
			yield True

		self.progressbar.set_text('Done')
		self.progress.set_text('')
		yield False

if __name__ == "__main__":
	(lang_code, encoding) = locale.getdefaultlocale()
	locale.setlocale(locale.LC_ALL, lang_code)

	checker = ThumbnailChecker()
	checker.show()

	gtk.main()
