"""
Commonly performed commands.
"""

import os
import os.path as op
import shutil
import logging
import ConfigParser

from functools import partial

from jcvi.utils.cbook import depends
from jcvi.apps.base import sh


def getpath(cmd, name=None, url=None, cfg="~/.jcvirc"):
    """
    Get install locations of common binaries
    First, check ~/.jcvirc file to get the full path
    If not present, ask on the console and and store
    """
    PATH = "Path"
    config = ConfigParser.RawConfigParser()
    cfg = op.expanduser(cfg)
    changed = False
    if op.exists(cfg):
        config.read(cfg)

    try:
        fullpath = config.get(PATH, name)
    except ConfigParser.NoSectionError:
        config.add_section(PATH)
        changed = True
    except:
        pass

    try:
        fullpath = config.get(PATH, name)
    except ConfigParser.NoOptionError:
        msg = "Set path for {0} [Blank if on your PATH]\n".\
                format(name, cfg)
        if url:
            msg += "URL: <{0}>\n>>> ".format(url)
        fullpath = raw_input(msg).strip()
        config.set(PATH, name, fullpath)
        changed = True

    if changed:
        configfile = open(cfg, "w")
        config.write(configfile)
        logging.debug("Configuration written to `{0}`.".format(cfg))

    path = op.join(fullpath, cmd)
    if not op.exists(path):
        path = cmd

    return path


BLPATH = partial(getpath, name="BLAST", url=\
        "ftp://ftp.ncbi.nlm.nih.gov/blast/executables/blast+/LATEST/")
BDPATH = partial(getpath, name="BEDTOOLS", url=\
        "http://code.google.com/p/bedtools/")
CAPATH = partial(getpath, name="Celera-Assembler", url=\
        "http://wgs-assembler.sf.net")
CDPATH = partial(getpath, name="CD-HIT", url=\
        "http://weizhong-lab.ucsd.edu/cd-hit/")
EMBOSSPATH = partial(getpath, name="EMBOSS", url=\
        "http://emboss.sourceforge.net/")
JAVAPATH = partial(getpath, name="Java1.6", url=\
        "http://www.java.com/")


@depends
def run_formatdb(infile=None, outfile=None):
    cmd = BLPATH("makeblastdb")
    cmd += " -dbtype nucl -in {0}".format(infile)
    sh(cmd)


@depends
def run_blat(infile=None, outfile=None, db="UniVec_Core", pctid=95, hitlen=50):
    cmd = 'blat {0} {1} -out=blast8 {2}'.format(db, infile, outfile)
    sh(cmd)

    blatfile = outfile
    filtered_blatfile = outfile + ".P{0}L{1}".format(pctid, hitlen)
    run_blast_filter(infile=blatfile, outfile=filtered_blatfile,
            pctid=pctid, hitlen=hitlen)
    shutil.move(filtered_blatfile, blatfile)


@depends
def run_vecscreen(infile=None, outfile=None, db="UniVec_Core",
        pctid=None, hitlen=None):
    """
    BLASTN parameters reference:
    http://www.ncbi.nlm.nih.gov/VecScreen/VecScreen_docs.html
    """
    nin = db + ".nin"
    run_formatdb(infile=db, outfile=nin)

    cmd = BLPATH("blastn")
    cmd += " -task blastn"
    cmd += " -query {0} -db {1} -out {2}".format(infile, db, outfile)
    cmd += " -penalty -5 -gapopen 4 -gapextend 4 -dust yes -soft_masking true"
    cmd += " -searchsp 1750000000000 -evalue 0.01 -outfmt 6 -num_threads 8"
    sh(cmd)


@depends
def run_megablast(infile=None, outfile=None, db=None, pctid=98, hitlen=100):
    nin = db + ".nin"
    run_formatdb(infile=db, outfile=nin)

    cmd = BLPATH("blastn")
    cmd += " -query {0} -db {1} -out {2}".format(infile, db, outfile)
    cmd += " -evalue 0.01 -outfmt 6 -num_threads 8"
    sh(cmd)

    blastfile = outfile
    filtered_blastfile = outfile + ".P{0}L{1}".format(pctid, hitlen)
    run_blast_filter(infile=blastfile, outfile=filtered_blastfile,
            pctid=pctid, hitlen=hitlen)
    shutil.move(filtered_blastfile, blastfile)


def run_blast_filter(infile=None, outfile=None, pctid=95, hitlen=50):
    from jcvi.formats.blast import filter

    logging.debug("Filter BLAST result (pctid={0}, hitlen={1})".\
            format(pctid, hitlen))
    pctidopt = "--pctid={0}".format(pctid)
    hitlenopt = "--hitlen={0}".format(hitlen)
    filter([infile, pctidopt, hitlenopt])