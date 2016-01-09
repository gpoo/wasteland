#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Waste land, Clean up unused thumbnails
#
# Copyright (C) 2006-2012 Germán Poo-Caamaño <gpoo@gnome.org>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

from gc import collect
import os
import os.path

import gi
gi.require_version('Gtk', '3.0')

from gi.repository import Gtk, GObject, Pango, Gio, GdkPixbuf

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
    OK, EXTERNAL, ORPHAN, NON_FD, INVALID = range(0, 5)

    def __init__(self):
        self.id = None
        self.first_time = True

        builder = Gtk.Builder()
        builder.add_from_file(os.path.join(os.path.dirname(__file__),
                                       'wasteland.glade'))
        self.model = Gtk.TreeStore(str, str, str)

        self.window = builder.get_object('window')
        self.treeview = builder.get_object('treeview')
        self.progressbar = builder.get_object('progressbar')
        self.progress = builder.get_object('progress')
        self.progress_uri = builder.get_object('uri')
        self.button_delete = builder.get_object('button_delete')
        self.button_start = builder.get_object('button_start')
        self.button_stop = builder.get_object('button_stop')
        builder.connect_signals(self)

        self.treeview.set_search_column(1)
        self.treeview.set_model(self.model)
        selection = self.treeview.get_selection()
        selection.set_mode(Gtk.SelectionMode.MULTIPLE)
        selection.connect("changed", self.on_selection_changed)

        renderer = Gtk.CellRendererText()
        renderer.set_property("ellipsize", Pango.EllipsizeMode.MIDDLE)
        column = Gtk.TreeViewColumn("File name or Thumbnail file",
                                    renderer, text=0)
        column.set_resizable(True)
        column.set_expand(True)
        self.treeview.append_column(column)

        renderer = Gtk.CellRendererText()
        renderer.set_property('xalign', 1.0)
        column = Gtk.TreeViewColumn("Size", renderer, text=1)
        column.set_resizable(True)
        column.set_min_width(80)
        column.set_resizable(True)
        self.treeview.append_column(column)

    def show(self):
        self.window.show_all()

    def on_quit(self, *args):
        Gtk.main_quit()

    def on_button_delete_clicked(self, button, *args):
        selection = self.treeview.get_selection()
        model, paths = selection.get_selected_rows()
        refs = []
        for path in paths:
            refs.append(Gtk.TreeRowReference.new(model, path))

        for ref in refs:
            path = ref.get_path()
            iter = model.get_iter(path)
            filename = model.get(iter, 2)[0]
            if filename is not None:
                os.unlink(os.path.expanduser(filename))
                model.remove(iter)

    def on_button_stop_clicked(self, button, *args):
        GObject.source_remove(self.id)
        self.button_stop.set_sensitive(False)
        self.button_start.set_sensitive(True)

    def on_button_start_clicked(self, button, *args):
        self.button_stop.set_sensitive(True)
        self.button_start.set_sensitive(False)
        if self.first_time:
            self.first_time = False
            self.task = self.walk()
        self.id = GObject.idle_add(self.task.next)

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
            text = "Processing %s:" % (os.path.basename(root))
            self.progress.set_text(text)

            for name in files:
                i = i + 1.0
                uri = None
                filename = os.path.join(root, name)

                self.progressbar.set_fraction(i / len(files))
                text = "%d of %d" % (i, len(files))
                self.progressbar.set_text(text)

                (result, resource, uri) = self.verify_thumbnail(filename)

                self.progress_uri.set_text(uri)

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

    def walk_done(self):
        GObject.source_remove(self.id)
        self.progressbar.set_text('Done')
        self.progress.set_text('')
        self.progress_uri.set_text('')
        self.button_stop.set_sensitive(False)

    def on_selection_changed(self, selection):
        has_selection = (selection.count_selected_rows () != 0)
        self.button_delete.set_sensitive(has_selection)

    def verify_thumbnail(self, filename):
        try:
            pixbuf = GdkPixbuf.Pixbuf.new_from_file(filename)
            uri = pixbuf.get_option('tEXt::Thumb::URI')
        except:
            # Broken thumbnail
            uri = ''

        gfile = Gio.File.new_for_uri(uri)
        path = gfile.get_path()

        if path is None and uri is not None and len(uri):
            return (self.EXTERNAL, uri, uri)
        if path and not os.path.lexists(path):
            return (self.ORPHAN, filename, uri)
        if uri is None:
            return (self.NON_FD, filename, uri)
        if len(uri) == 0:
            return (self.INVALID, filename, uri)
        return (self.OK, filename, uri)

    def compute(self, filename, item, element, text):
        sum_size = getattr(self, item + '_size')
        counter = getattr(self, item + '_count')
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

    Gtk.main()
