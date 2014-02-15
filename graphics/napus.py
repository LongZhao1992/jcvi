#!/usr/bin/env python
# -*- coding: UTF-8 -*-

"""
Functions in this script produce figures in the various past manuscripts.
"""

import os.path as op
import sys
import logging

import numpy as np

from jcvi.graphics.base import plt, _, Rectangle, Polygon, CirclePolygon, \
        savefig, mpl, cm, adjust_spines
from jcvi.graphics.glyph import GeneGlyph, RoundLabel, RoundRect, \
        arrowprops, TextCircle, plot_cap
from jcvi.graphics.chromosome import Chromosome
from jcvi.graphics.karyotype import Karyotype
from jcvi.graphics.synteny import Synteny, draw_gene_legend
from jcvi.graphics.coverage import Coverage, Sizes, XYtrack, setup_gauge_ax
from jcvi.utils.iter import pairwise
from jcvi.apps.base import OptionParser, ActionDispatcher, fname, debug
debug()


template_cov = """# y, xstart, xend, rotation, color, label, va, bed
.56, {0}, {1}, 0, darkslategray, , top, AN.bed
.48, {2}, {3}, 0, darkslategray, , top, CN.bed
# edges
e, 0, 1, AN.CN.1x1.lifted.simple
"""
template_f3a = """# y, xstart, xend, rotation, color, label, va, bed
.9, {0}, {1}, 0, gainsboro, B. napus A2, top, AN.bed
.75, {2}, {3}, 0, gainsboro, B. rapa A2, top, brapa.bed
.6, {4}, {5}, 0, gainsboro, B. oleracea C2, top, boleracea.bed
.45, {6}, {7}, 0, gainsboro, B. napus C2, top, CN.bed
# edges
e, 0, 1, AN.brapa.1x1.lifted.simple
e, 1, 2, brapa.boleracea.1x1.lifted.simple
e, 3, 2, CN.boleracea.1x1.lifted.simple
"""
gap = .03


def main():

    actions = (
        ('ploidy', 'plot napus macro-synteny (requires data)'),
        ('expr', 'plot expression values between homeologs (requires data)'),
        ('cov', 'plot coverage graphs between homeologs (requires data)'),
        ('deletion', 'plot histogram for napus deletions (requires data)'),
        ('f3a', 'plot figure-3a'),
            )
    p = ActionDispatcher(actions)
    p.dispatch(globals())


def calc_ratio(chrs, sizes):
    chr_sizes = [[sizes.get_size(x) for x in z] for z in chrs]
    chr_sum_sizes = [sum(x) for x in chr_sizes]
    ratio = .8 / max(chr_sum_sizes)
    return chr_sizes, chr_sum_sizes, ratio


def center_panel(chr, chr_size, ratio, gap=gap):
    # Center two panels
    w = (ratio * chr_size + (len(chr) - 1) * gap) / 2
    return .5 - w, .5 + w


def make_seqids(chrs, seqidsfile="seqids"):
    seqidsfile = "seqids"
    fw = open(seqidsfile, "w")
    for chr in chrs:
        print >> fw, ",".join(chr)
    fw.close()
    logging.debug("File `{0}` written.".format(seqidsfile))
    return seqidsfile


def make_layout(chrs, chr_sizes, ratio, template, klayout="layout"):
    coords = []
    for chr, chr_size in zip(chrs, chr_sizes):
        coords.extend(center_panel(chr, chr_size, ratio))

    klayout = "layout"
    fw = open(klayout, "w")
    print >> fw, template.format(*coords)
    fw.close()
    logging.debug("File `{0}` written.".format(klayout))

    return klayout


def cov(args):
    """
    %prog cov chrA01 chrC01 chr.sizes data AN.CN.1x1.lifted.anchors.simple

    Plot coverage graphs between homeologs, the middle panel show the
    homeologous gene pairs. Allow multiple chromosomes to multiple chromosomes.
    """
    p = OptionParser(cov.__doc__)
    p.add_option("--order",
                default="swede,kale,h165,yudal,aviso,abu,bristol,bzh",
                help="The order to plot the tracks, comma-separated")
    p.add_option("--gauge_step", default=5000000, type="int",
                help="Step size for the base scale")
    p.add_option("--hlsuffix", default="regions.forhaibao",
                help="Suffix for the filename to be used to highlight regions")
    opts, args, iopts = p.set_image_options(args, figsize="11x8")

    if len(args) != 4:
        sys.exit(not p.print_help())

    chr1, chr2, sizes, datadir = args
    chr1 = chr1.split(",")
    chr2 = chr2.split(",")

    order = opts.order
    hlsuffix = opts.hlsuffix
    if order:
        order = order.split(",")
    sizes = Sizes(sizes)
    fig = plt.figure(1, (iopts.w, iopts.h))
    root = fig.add_axes([0, 0, 1, 1])

    chrs = (chr1, chr2)
    chr_sizes, chr_sum_sizes, ratio = calc_ratio(chrs, sizes)
    chr_size1, chr_size2 = chr_sum_sizes
    chr_sizes1, chr_sizes2 = chr_sizes

    w1_start, w1_end = center_panel(chr1, chr_size1, ratio)
    w2_start, w2_end = center_panel(chr2, chr_size2, ratio)
    w1s = w1_start
    w2s = w2_start

    i = 0
    for c1, s1 in zip(chr1, chr_sizes1):
        w1 = ratio * s1
        canvas1 = (w1s, .6, w1, .3)
        plot_label = i == 0
        i += 1
        c = Coverage(fig, root, canvas1, c1, (0, s1), datadir,
                     order=order, gauge="top", plot_label=plot_label,
                     gauge_step=opts.gauge_step,
                     hlsuffix=hlsuffix)
        w1s += w1 + gap

    i = 0
    for c2, s2 in zip(chr2, chr_sizes2):
        w2 = ratio * s2
        canvas2 = (w2s, .15, w2, .3)
        plot_label = i == 0
        i += 1
        c = Coverage(fig, root, canvas2, c2, (0, s2), datadir,
                     order=order, gauge="bottom", plot_label=plot_label,
                     hlsuffix=hlsuffix)
        w2s += w2 + gap

    # Synteny panel
    seqidsfile = make_seqids(chrs)
    klayout = make_layout(chrs, chr_sum_sizes, ratio, template_cov)
    Karyotype(fig, root, seqidsfile, klayout, gap=gap, generank=False)

    root.set_xlim(0, 1)
    root.set_ylim(0, 1)
    root.set_axis_off()

    chr2 = "_".join(chr2)
    image_name = chr2 + "." + iopts.format
    savefig(image_name, dpi=iopts.dpi, iopts=iopts)


def conversion_track(order, filename, col, label, ax, color):
    from jcvi.formats.bed import Bed

    ids = []
    fp = open(filename)
    for row in fp:
        atoms = row.split()
        gid = atoms[col].replace('T', 'G')
        ids.append(gid)

    beds = [order[x][1] for x in ids if x in order]
    pts = [x.start for x in beds if x.seqid == label]
    logging.debug("A total of {0} converted loci imported.".format(len(pts)))

    ax.scatter(pts, len(pts) * [0], s=4, c=color, edgecolors="none")
    ax.set_axis_off()


def make_affix_axis(fig, t, yoffset, height=.001):
    x, y = t.xstart, t.y + yoffset
    w = t.xend - t.xstart
    ax = fig.add_axes([x, y, w, height])
    start, end = 0, t.total
    ax.set_xlim(start, end)
    return ax


def f3a(args):
    """
    %prog f3a chrA02,A02,C2,chrC02 chr.sizes data

    Napus Figure 3A displays alignments between quartet chromosomes, inset
    with read histograms.
    """
    from jcvi.formats.bed import Bed

    p = OptionParser(f3a.__doc__)
    p.add_option("--gauge_step", default=10000000, type="int",
                help="Step size for the base scale")
    opts, args, iopts = p.set_image_options(args, figsize="11x8")

    if len(args) != 3:
        sys.exit(not p.print_help())

    chrs, sizes, datadir = args
    gauge_step = opts.gauge_step
    chrs = [[x] for x in chrs.split(",")]
    sizes = Sizes(sizes)
    height = .08

    fig = plt.figure(1, (iopts.w, iopts.h))
    root = fig.add_axes([0, 0, 1, 1])

    chr_sizes, chr_sum_sizes, ratio = calc_ratio(chrs, sizes)

    # Synteny panel
    seqidsfile = make_seqids(chrs)
    klayout = make_layout(chrs, chr_sum_sizes, ratio, template_f3a)
    K = Karyotype(fig, root, seqidsfile, klayout, gap=gap,
                  height=height, lw=2, generank=False)

    # Inset with datafiles
    datafiles = ("chrA02.bzh.forxmgr", "parent.A02.per10kb.forxmgr",
                 "parent.C2.per10kb.forxmgr", "chrC02.bzh.forxmgr")
    datafiles = [op.join(datadir, x) for x in datafiles]
    tracks = K.tracks
    r = height / 4
    for t, datafile in zip(tracks, datafiles):
        ax = make_affix_axis(fig, t, -r, height=2 * r)
        XYtrack(ax, datafile, color="lightslategray").draw()
        start, end = 0, t.total
        gauge_ax = make_affix_axis(fig, t, -r)
        adjust_spines(gauge_ax, ["bottom"])
        setup_gauge_ax(gauge_ax, start, end, gauge_step)

    # Converted gene tracks
    ax_AN = make_affix_axis(fig, tracks[0], r, height=r/2)
    ax_CN = make_affix_axis(fig, tracks[-1], r, height=r/2)

    order = Bed("napus.bed").order
    conversion_track(order, "data/Genes.Converted.seuil.0.6.AtoC.txt",
                     2, "chrA02", ax_AN, "b")
    conversion_track(order, "data/Genes.Converted.seuil.0.6.CtoA.txt",
                     3, "chrC02", ax_CN, "g")

    root.set_xlim(0, 1)
    root.set_ylim(0, 1)
    root.set_axis_off()

    image_name = "napusf3a." + iopts.format
    savefig(image_name, dpi=iopts.dpi, iopts=iopts)


def deletion(args):
    """
    %prog deletion [deletion-genes|deletion-bases] C2-deletions boleracea.bed

    Plot histogram for napus deletions. Can plot deletion-genes or
    deletion-bases. The three largest segmental deletions will be highlighted
    along with a drawing of the C2 chromosome.
    """
    import math
    from jcvi.formats.bed import Bed
    from jcvi.graphics.glyph import TextCircle
    from jcvi.graphics.chromosome import HorizontalChromosome
    from jcvi.graphics.base import kb_formatter

    p = OptionParser(deletion.__doc__)
    opts, args, iopts = p.set_image_options(args)

    if len(args) != 3:
        sys.exit(not p.print_help())

    deletion_genes, deletions, bed = args
    dg = [int(x) for x in open(deletion_genes)]
    dsg, lsg = "darkslategray", "lightslategray"

    fig = plt.figure(1, (iopts.w, iopts.h))
    root = fig.add_axes([0, 0, 1, 1])
    ax = fig.add_axes([.1, .1, .8, .8])
    minval = 2 if deletion_genes == "deleted-genes" else 2048
    bins = np.logspace(math.log(minval, 10), math.log(max(dg), 10), 16)
    n, bins, histpatches = ax.hist(dg, bins=bins, \
                                   fc=lsg, alpha=.75)
    ax.set_xscale('log', basex=2)
    if deletion_genes == "deleted-genes":
        ax.xaxis.set_major_formatter(mpl.ticker.FormatStrFormatter('%d'))
        ax.set_xlabel('No. of deleted genes in each segment')
    else:
        ax.xaxis.set_major_formatter(kb_formatter)
        ax.set_xlabel('No. of deleted bases in each segment')
    ax.yaxis.set_major_formatter(mpl.ticker.FormatStrFormatter('%d'))
    ax.set_ylabel('No. of segments')
    ax.patch.set_alpha(0.1)

    # Draw chromosome C2
    na, nb = .45, .85
    root.text((na + nb) / 2, .54, "ChrC02", ha="center")
    hc = HorizontalChromosome(root, na, nb, .5, height=.025,
                             fc=lsg, fill=True)

    order = Bed(bed).order
    fp = open(deletions)
    scale = lambda x: na + x * (nb - na) / 52886895
    for i, row in enumerate(fp):
        i += 1
        num, genes = row.split()
        genes = genes.split("|")
        ia, a = order[genes[0]]
        ib, b = order[genes[-1]]
        mi, mx = a.start, a.end
        mi, mx = scale(mi), scale(mx)
        root.add_patch(Rectangle((mi, .475), mx - mi, .05,
                       fc="red", ec="red"))
        if i == 1:   # offset between two adjacent regions for aesthetics
            mi -= .015
        elif i == 2:
            mi += .015
        TextCircle(root, mi, .44, str(i), fc="red")

    for i, mi in zip(range(1, 4), (.83, .78, .73)):
        TextCircle(root, mi, .2, str(i), fc="red")

    root.set_xlim(0, 1)
    root.set_ylim(0, 1)
    root.set_axis_off()

    image_name = deletion_genes + ".pdf"
    savefig(image_name, dpi=iopts.dpi, iopts=iopts)


def ploidy(args):
    """
    %prog ploidy seqids layout

    Build a figure that calls graphics.karyotype to illustrate the high ploidy
    of B. napus genome.
    """
    p = OptionParser(ploidy.__doc__)
    opts, args, iopts = p.set_image_options(args, figsize="8x7")

    if len(args) != 2:
        sys.exit(not p.print_help())

    seqidsfile, klayout = args

    fig = plt.figure(1, (iopts.w, iopts.h))
    root = fig.add_axes([0, 0, 1, 1])

    Karyotype(fig, root, seqidsfile, klayout)

    fc = "lightslategrey"
    radius = .012
    ot = -.05  # use this to adjust vertical position of the left panel
    TextCircle(root, .1, .9 + ot, r'$\gamma$', radius=radius, fc=fc)
    root.text(.1, .88 + ot, r"$\times3$", ha="center", va="top", color=fc)
    TextCircle(root, .08, .79 + ot, r'$\alpha$', radius=radius, fc=fc)
    TextCircle(root, .12, .79 + ot, r'$\beta$', radius=radius, fc=fc)
    root.text(.1, .77 + ot, r"$\times3\times2\times2$", ha="center", va="top", color=fc)
    root.text(.1, .67 + ot, r"Brassica triplication", ha="center",
                va="top", color=fc, size=11)
    root.text(.1, .65 + ot, r"$\times3\times2\times2\times3$", ha="center", va="top", color=fc)
    root.text(.1, .42 + ot, r"Allo-tetraploidy", ha="center",
                va="top", color=fc, size=11)
    root.text(.1, .4 + ot, r"$\times3\times2\times2\times3\times2$", ha="center", va="top", color=fc)

    bb = dict(boxstyle="round", fc="w", ec="0.5", alpha=0.5)
    root.text(.5, .2 + ot, "Brassica napus", ha="center",
                size=18, color="g", bbox=bb)

    root.set_xlim(0, 1)
    root.set_ylim(0, 1)
    root.set_axis_off()

    pf = "napus"
    image_name = pf + "." + iopts.format
    savefig(image_name, dpi=iopts.dpi, iopts=iopts)


def expr(args):
    """
    %prog expr block exp layout napus.bed

    Plot a composite figure showing synteny and the expression level between
    homeologs in two tissues - total 4 lists of values. block file contains the
    gene pairs between AN and CN.
    """
    from matplotlib.colors import LogNorm
    from jcvi.graphics.base import red_purple as default_cm

    p = OptionParser(expr.__doc__)
    opts, args, iopts = p.set_image_options(args, figsize="8x7")

    if len(args) != 4:
        sys.exit(not p.print_help())

    block, exp, layout, napusbed = args

    fig = plt.figure(1, (iopts.w, iopts.h))
    root = fig.add_axes([0, 0, 1, 1])
    s = Synteny(fig, root, block, napusbed, layout)
    draw_gene_legend(root, .22, .55, .57)

    # Import the expression values
    # Columns are: leaf-A, leaf-C, root-A, root-C
    pairs = [row.split() for row in open(block)]
    data = np.loadtxt(exp)
    nrows = len(pairs)
    assert data.shape[0] == nrows, "block and exp row counts mismatch"
    A = data[:, [2, 0]]
    C = data[:, [3, 1]]
    A = np.transpose(A)
    C = np.transpose(C)

    x, y, d, w, h = .18, .64, .008, .65, .08
    lsg = "lightslategrey"
    coords = s.gg  # Coordinates of the genes
    Ag = [p[0] for p in pairs]
    Cg = [p[1] for p in pairs]

    for y, Gg in ((.64, Ag), (.29, Cg)):
        root.add_patch(Rectangle((x - h, y - d), w + h + d, h + 2 * d, fill=False,
                                ec=lsg, lw=1))
        root.text(x - d, y + 3 * h / 4, "leaf", ha="right", va="center")
        root.text(x - d, y + h / 4, "root", ha="right", va="center")
        ty = y - 2 * d if y > .5 else y + h + 2 * d
        for i, g in enumerate(Gg):
            start, end = coords[g]
            sx, sy = start
            ex, ey = end
            assert sy == ey
            sy = sy + 2 * d if sy > .5 else sy - 2 * d
            root.plot(((sx + ex) / 2, x + w * (i + .5)/ nrows), (sy, ty),
                            lw=2, ls=":", color="k", alpha=.2)

    axA = fig.add_axes([x, .64, w, h])
    axC = fig.add_axes([x, .29, w, h])

    norm = LogNorm(1, 10000)
    p = axA.pcolormesh(A, cmap=default_cm, norm=norm)
    p = axC.pcolormesh(C, cmap=default_cm, norm=norm)
    axA.set_xlim(0, nrows)
    axC.set_xlim(0, nrows)

    x, y, w, h = .35, .17, .3, .03
    ax_colorbar = fig.add_axes([x, y, w, h])
    fig.colorbar(p, cax=ax_colorbar, orientation='horizontal')
    root.text(x - d, y + h / 2, "RPKM", ha="right", va="center")

    root.set_xlim(0, 1)
    root.set_ylim(0, 1)
    for x in (axA, axC, root):
        x.set_axis_off()

    pf = "napusexp"
    image_name = pf + "." + iopts.format
    savefig(image_name, dpi=iopts.dpi, iopts=iopts)


if __name__ == '__main__':
    main()