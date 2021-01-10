# ldraw-parts
LDRAW parts mirror repository, used for python-ldraw

In the orphan branch `library`, there is a series of commits representing the different updates. 
From 0.27 beta (base, original release), The different updates are applied sequentially then tagged.

To download a .zip containing a particular version, just download 

https://github.com/rienafairefr/ldraw-parts/archive/<version>.zip

The repo itself is not really meant to be run, but what it does is:

- get the release list (using https://www.ldraw.org/cgi-bin/ptreleases.cgi) 
- download archives from www.ldraw.org at http://www.ldraw.org/library/updates/<filename>.<zip/exe>
- merge the versions
    e.g. to get 2008-01, you go back to 1997-16 then extract all the updates into one directory, 
    up to and including the 2008-01 release 
- create an orphan branch `library`
- sequentially add the library files into that repo, commit, tag, push

hacky: 
ldraw was made on windows, so there's some legacy/inconsistencies in case, LDRAW/ldraw, PART/parts, etc.
I made loopedback FAT32 directory to do the version merging properly, as if it was done on a FAT Windows partition

might be interesting to do:
- recover the moves (e.g. 257 -> ~257) "git mv"
- recover authors (stored in files) & present history of each update as a merged branch 
