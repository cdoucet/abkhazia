# Copyright 2016 Thomas Schatz, Xuan Nga Cao, Mathieu Bernard
#
# This file is part of abkhazia: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Abkhazia is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with abkhazia. If not, see <http://www.gnu.org/licenses/>.
"""Implementation of the 'abkhazia decode' command"""

import multiprocessing
import os

from abkhazia.commands.abstract_command import AbstractRecipeCommand
from abkhazia.kaldi.abkhazia2kaldi import add_argument
import abkhazia.kaldi.decode as decode
import abkhazia.utils as utils


class AbkhaziaDecode(AbstractRecipeCommand):
    name = 'decode'

    description = """compute phone posteriograms or transcription from a language model,
    an acoustic model and an abkhazia corpus to be decoded"""

    @classmethod
    def add_parser(cls, subparsers):
        """Return a parser for the align command"""
        # get basic parser init from AbstractCommand
        parser, dir_group = super(AbkhaziaDecode, cls).add_parser(subparsers)

        parser.add_argument(
            '-j', '--njobs-train', type=int, metavar='<njobs>',
            default=multiprocessing.cpu_count(),
            help="""number of jobs to launch for parallel alignment, default is to
            launch %(default)s jobs.""")

        dir_group.add_argument(
            '-l', '--language-model', metavar='<lm-dir>', default=None,
            help='''the language model recipe directory, data is read from
            <lm-dir>/language. If not specified, use <lm-dir>=<corpus>.''')

        dir_group.add_argument(
            '-a', '--acoustic-model', metavar='<am-dir>', default=None,
            help='''the acoustic model recipe directory, data is read from
            <am-dir>/acoustic. If not specified, use <am-dir>=<corpus>.''')

        dir_group.add_argument(
            '-m', '--mfcc-features', metavar='<feat-dir>', default=None,
            help='''the features directory, data is read from
            <feat-dir>/features/mfcc. If not specified, use <feat-dir>=<corpus>.''')

        group = parser.add_argument_group(
            'decoding parameters', 'those parameters can also be '
            'specified in the [decode] section of the configuration file')

        def config(param):
            return utils.config.get(cls.name, param)

        group.add_argument(
            '-s', '--acoustic-scale', type=float, metavar='<float>',
            default=config('acoustic-scale'),
            help='''acoustic scale for extracting posterior
            from the final lattice, default is %(default)s''')

        return parser

    @classmethod
    def run(cls, args):
        corpus, output_dir = cls.prepare_for_run(args)

        # get back the features directory
        feat = (corpus if args.mfcc_features is None
                else os.path.abspath(args.mfcc_features))
        feat += '/features'

        # get back the language model directory
        lang = (corpus if args.language_model is None
                else os.path.abspath(args.language_model))
        lang += '/language/lang'

        # get back the acoustic model directory
        acoustic = (corpus if args.acoustic_model is None
                    else os.path.abspath(args.acoustic_model))
        acoustic += '/acoustic/exp/acoustic_model'

        # instanciate the kaldi recipe
        recipe = decode.Decode(corpus, output_dir, args.verbose)

        # setup recipe parameters
        recipe.feat_dir = feat
        recipe.lm_dir = lang
        recipe.am_dir = acoustic
        recipe.acoustic_scale = args.acoustic_scale
        recipe.njobs_train = args.njobs_train

        # finally create and/or run the recipe
        recipe.create(args)
        recipe.run()
        recipe.export()
