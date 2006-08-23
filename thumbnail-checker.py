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

class ThumbnailChecker:
	def __init__(self):
		xml = gtk.glade.XML('thumbnail-checker.glade', None, None)
		self.model = gtk.ListStore(str, str, int)

		self.window = xml.get_widget('window')
		treeview = xml.get_widget('treeview')
		self.non_fd_count = xml.get_widget('non_fd_count')
		self.non_fd_size = xml.get_widget('non_fd_size')
		self.invalid_count = xml.get_widget('invalid_count')
		self.invalid_size = xml.get_widget('invalid_size')
		self.orphan_count = xml.get_widget('orphan_count')
		self.orphan_size = xml.get_widget('orphan_size')
		self.progressbar = xml.get_widget('progressbar')
		xml.signal_autoconnect(self)

		treeview.set_search_column(1)
		treeview.set_model(self.model)

		renderer = gtk.CellRendererText()
		column = gtk.TreeViewColumn("Type", renderer, text=0)
		treeview.append_column(column)
		
		renderer = gtk.CellRendererText()
		column = gtk.TreeViewColumn("File name or Thumbnail file", renderer, text=1)
		column.set_sizing(gtk.TREE_VIEW_COLUMN_FIXED)
		column.set_fixed_width(400)
		treeview.append_column(column)

		renderer = gtk.CellRendererText()
		column = gtk.TreeViewColumn("Size", renderer, text=2)
		treeview.append_column(column)

	def show(self):
		self.window.show_all()

	def on_quit(self, *args):
		gtk.main_quit()

	def on_button_start_clicked(self, button, *args):
		self.work = True
		button.set_sensitive(True)
		self.walk()

	def walk(self, *args):
		non_fd = { 'size': 0, 'count': 0 }
		non_thumb = { 'size': 0, 'count': 0 }
		orphan_thumb = { 'size': 0, 'count': 0 }
		space_wasted = 0
		
		rootdir = os.path.expanduser('~/.thumbnails')
		for root, dirs, files in os.walk(rootdir):
			#print sum(getsize(join(root, name)) for name in files),

			print 'root:', root, '# files', len(files)
			text = "%d of %d" % (0, len(files))
			self.progressbar.set_text(text)
			i = 0.0

			for name in files:
				i = i + 1.0
				filename = join(root, name)
				uri = None

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
					print 'gnomevfs', uri
					local_path = ''

				if len(local_path) and not os.path.lexists(local_path):
					# orphan thumbnail
					size = getsize(filename)
					orphan_thumb['size'] += size
					orphan_thumb['count'] += 1

					print 'Orphaner!!!', local_path
					self.orphan_count.set_text(str(orphan_thumb['count']))
					self.orphan_size.set_text(str(orphan_thumb['size']))

					self.model.append(['Orphan', local_path, size])
				elif uri is None:
					# pixbuf is ok, but no FD compliant.
					#print "==> %s has not URI: %s" % (filename, uri)
					size = getsize(filename)
					non_fd['size'] += size
					non_fd['count'] += 1

					self.non_fd_count.set_text(str(non_fd['count']))
					self.non_fd_size.set_text(str(non_fd['size']))

					self.model.append(['Non FD', filename, size])
				elif len(uri) == 0:
					# thumbnail is not a valid pixbuf
					size = getsize(filename)
					non_thumb['size'] += size
					non_thumb['count'] += 1

					self.invalid_count.set_text(str(non_thumb['count']))
					self.invalid_size.set_text(str(non_thumb['size']))

					self.model.append(['Invalid', filename, size])

				while gtk.events_pending():
					gtk.main_iteration()

				collect()

if __name__ == "__main__":
	checker = ThumbnailChecker()
	checker.show()

	gtk.main()
