Waste land
==========

``Waste land`` is an script to estimate and clean up the wasted space in
unused thumbnails in your home directory (in Free Desktops).

Thumbnails are small images (less than 50KiB) that help applications to
show a fast preview of files (pictures, videos, text documents, etc.). For
details, see [Thumbnail Managing Standard][1].

  [1]: http://specifications.freedesktop.org/thumbnail-spec/thumbnail-spec-latest.html

Thumbnails are associated with files. When those files are moved, the 
association can be lost, leaving the thumbnails orphan.  Although the space
required by each thumbnail is very small, it can grow more than you think.

How big can it be?
------------------

The thumbnails are stored in directories `normal`, `large` and `fail`. For
instance, if you have thounsands of pictures stored in different directories
in `Pictures/Downdloads`, then you could have thousands of thumbnails either 
in `normal`, `large` or both.  If you decide to move them to
`Pictures/Reviewed`, likely you will have twice the thumbnails than before.
The thumbnails are created on demand, so it will not happen overnight.  But
it will happen at some point.

When you connect a camera or phone, likely, you will get thumbnails
generated as you browse them.  So, the next time you connect those devices
the thumbnails would be there and you can browse them faster... only if
you still have the same pictures in your camera (unlikely) and if you 
connect the camera to the same usb port.

I wrote this script in 2006, for my own purpose.  However, one weekend, when 
helping to do a backup (mirror) of a whole home directory, I noticed
that `rsync` was stuck in `~/.thumbnails/normal`.  I instructed `rsync` to 
skip `~/.thumbnails` and it was fast again (relatively). It seems `rsync`
pays a toll in very populated directories.  When I ran `waste land`, there
were more than 45,000 orphan thumbnails using more than 750MB of space.
Your mileage may vary.

I had not share the script before because I consider it a quick hack.
It does not solve the problem, just a symptom.  However, it would be worse
to delete the `.thumbnails` directory from time to time.