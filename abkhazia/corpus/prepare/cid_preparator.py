# coding: utf-8
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
"""Data preparation for the CID corpus"""

import os

import abkhazia.utils as utils
from abkhazia.corpus.prepare import AbstractPreparator


class CIDPreparator(AbstractPreparator):
    """Convert the CID corpus to the abkhazia format"""

    name = 'cid'
    description = 'Corpus of Interactional Data'

    long_description = '''
    Le CID (Corpus d'interactions dialogales / Corpus of Interactional
    Data) est un corpus audio-video de 8 heures, en français, destiné
    à l'annotation multimodale qui inclut la phonétique, la prosodie,
    la morphologie, la syntaxe, le discours et la mimo-gestualité.
    '''
    url = 'https://www.ortolang.fr/market/corpora/sldr000720'
    audio_format = 'wav'

    # IPA transcriptions for all phones in the CID corpus.
    phones = {
        '@': u'ə',
        'a~': u'ɑ̃',
        'A': u'a',
        'b': u'b',
        'd': u'd',
        'e': u'e',
        'f': u'f',
        'g': u'g',
        'H': u'ɥ',
        'i': u'i',
        'j': u'j',
        'k': u'k',
        'l': u'l',
        'm': u'm',
        'n': u'n',
        'o~': u'ɔ̃',
        'o': u'o',
        'p': u'p',
        'R': u'ʁ',
        's': u's',
        'S': u'ʃ',
        't': u't',
        'u': u'u',
        'U~': u'ɛ̃',
        'v': u'v',
        'w': u'w',
        'y': u'y',
        'z': u'z',
        'Z': u'ʒ'
    }

    silences = [u"SIL_WW", u"NSN"]  # SPN and SIL will be added automatically

    variants = []  # could use lexical stress variants...

    def __init__(self, input_dir, log=utils.logger.null_logger(),
                 copy_wavs=False):
        super(CIDPreparator, self).__init__(input_dir, log=log)
        self.copy_wavs = copy_wavs

    def _yield_transcription(self, trs_file):
        """Yield (utt, wav, text, tstart, tstop) read from transcription

        Utterances containing only gpf_* are ignored as they contain
        no clean speech

        """
        # speaker id are the first 2 letters of the file
        spk = os.path.basename(trs_file)[:2]

        utt, tstart, tstop, text = None, None, None, None
        for line in (l.strip() for l in utils.open_utf8(trs_file, 'r')):
            if line.startswith('intervals ['):
                utt = spk + '_' + line.split('[')[1][:-2]
                tstart, tstop = None, None
            elif line.startswith('xmin'):
                tstart = float(line.split(' = ')[1])
            elif line.startswith('xmax'):
                tstop = float(line.split(' = ')[1])
            elif line.startswith('text'):
                text = line.split(' = ')[1].replace('"', '')

            if utt and tstart and tstop and text:
                if not text.startswith('gpf_'):
                    yield utt, spk + '-anonym', text, tstart, tstop
                    utt, tstart, tstop, text = None, None, None, None

    def list_audio_files(self):
        return utils.list_files_with_extension(
            os.path.join(self.input_dir, 'wav'), '.wav', abspath=True)

    def make_segment(self):
        segments = dict()

        # transcription files are CID/TextGrid/*transcription*.TextGrid
        trs_files = (t for t in utils.list_directory(
            os.path.join(self.input_dir, 'TextGrid'), abspath=True)
                     if 'transcription' in os.path.basename(t))
        for trs in trs_files:
            for utt, wav, _, tstart, tstop in self._yield_transcription(trs):
                segments[utt] = (wav, tstart, tstop)
        return segments

    def make_speaker(self):
        return {k: k[:2] for k in self.make_segment().iterkeys()}

    def make_transcription(self):
        text = dict()

        # transcription files are CID/TextGrid/*transcription*.TextGrid
        trs_files = (t for t in utils.list_directory(
            os.path.join(self.input_dir, 'TextGrid'), abspath=True)
                     if 'transcription' in os.path.basename(t))
        for trs_file in trs_files:
            for utt, _, txt, _, _ in self._yield_transcription(trs_file):
                text[utt] = txt
        return text

  
    def make_lexicon(self):        ## TODO: fix "spelling" to account for speech errors, etc
        dict_word = dict()
        ## word files are CID/TextGrid/*tokens*.TextGrid
        tok_files = (t for t in utils.list_directory(
            os.path.join(self.input_dir, 'TextGrid'), abspath=True)
                     if 'tokens' in os.path.basename(t))
        for tok_file in tok_files:
            spk = os.path.basename(tok_file)[:2]
            phon_file = os.path.join(self.input_dir, 'TextGrid', spk + "-phonemes.TextGrid")
            token, tstart, tstop = None, None, None
            t1, t2 = 0, 0
            
            dummy = False
            wd = list()
            phn = list()

            ## get word and time intervals
            for line in (l.strip() for l in utils.open_utf8(tok_file, 'r')):
                if dummy == True:
                    line = line.replace('"', '')
                    wd.append(line.encode("utf-8"))
                    if len(wd) == 3:
                        tstart, tstop, token = wd
                        tstart, tstop = float(tstart), float(tstop)
                        wd = list()

                        ## find phonetic transcription in phonemes file
                        cnt = 0
                        for pline in (pl.strip() for pl in utils.open_utf8(phon_file, 'r')):
                            cnt += 1
                            pline = pline.encode("utf-8")
                            if (cnt + 2) % 3 == 0:
                                t1 = pline
                            if (cnt + 1) % 3 == 0:
                                t2 = pline
                            if cnt % 3 == 0:
                                if str.isdigit(t1.replace(".", "")) == True and str.isdigit(t2.replace(".", "")) == True:
                                    if tstart <= float(t1) < tstop and tstart < float(t2) <= tstop:
                                        phn.append(pline.replace('"', ''))
                                        
                                else:
                                    phn = list()
                        if token != "#":
                            dict_word[token] = phn #' '.join(phn)
                            #print tstart, tstop, token, phn
                            #cnt = 0
                else:
                    if '\"dummy\"' in line:
                        dummy = True
        return dict_word     

