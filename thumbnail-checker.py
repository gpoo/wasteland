#!/usr/bin/env python

import gtk
import gtk.gdk
import gnome.ui
import gnomevfs
import os
import gc

filename = "/home/gpoo/.thumbnails/large/007ec399237ea661fd3f699e99aa7908.png"

class ThumbnailCheck:
	def __init__(self):
		self.model = gtk.ListStore(str, str, int)

		self.window = gtk.Window()
		self.window.set_default_size(640, 480)
		self.window.connect('delete_event', gtk.main_quit, None)

		sw = gtk.ScrolledWindow()
		sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)

		treeview = gtk.TreeView()
		treeview.set_rules_hint(True)
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

		sw.add(treeview)

		button = gtk.Button(label='Start')
		button.connect("clicked", self.on_button_clicked, None)

		vbox = gtk.VBox()
		vbox.set_spacing(12)
		vbox.set_border_width(6)

		vbox.pack_start(sw)
		vbox.pack_end(button, expand=False)

		self.window.add(vbox)

	def is_valid(self, pixbuf):
		uri = pixbuf.get_option('tEXt::Thumb::URI')
		local_filename = gnomevfs.get_local_path_from_uri(uri)

		try:
			os.stat(local_filename)
			return True
		except:
			return False

	def show(self):
		self.window.show_all()

	def on_button_clicked(self, button, *args):
		button.set_sensitive(False)
		self.walk()

	def walk(self, *args):
		#self.model.clear()

		from os.path import join, getsize
		rootdir = os.path.expanduser('~/.thumbnails')
		for root, dirs, files in os.walk(rootdir):
			total_size = 0
			#print sum(getsize(join(root, name)) for name in files),

			for name in files:
				filename = join(root, name)
				uri = None
				size = 0

				try:
					pixbuf = gtk.gdk.pixbuf_new_from_file(filename)
					uri = pixbuf.get_option('tEXt::Thumb::URI')
				except:
					#print "Pixbuf Error", filename
					uri = None

				try:
					local_path = gnomevfs.get_local_path_from_uri(uri)
				except:
					local_path = ''

				if not uri:
					#print "==> %s has not URI: %s" % (filename, uri)
					size = getsize(filename)
					self.model.append(['No FD', filename, size])
				elif local_path and not os.path.lexists(local_path):
					size = getsize(filename)
					#print "No existe: %s" % local_path
					self.model.append(['No file', local_path, size])

				total_size += size

				while gtk.events_pending():
					gtk.main_iteration(False)

				gc.collect()

			print "Total size of %s: %s in %d files" % (root, total_size, len(files))

if __name__ == "__main__":
	c = ThumbnailCheck()

	c.show()

	gtk.main()
