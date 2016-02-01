# coding: utf-8

"""Data preparation for the LibriSpeech corpus

The raw distribution of LibriSpeech is available at
http://www.openslr.org/12/

In addition to the LibriSpeech corpus, this preparator need the CMU
and LibriSpeech dictionaries. The CMU dictionary is available for free
at http://www.speech.cs.cmu.edu/cgi-bin/cmudict.  The preparator is
designed for version 0.7a of the CMU dictionary, but other recent
versions could probably be used without changing anything

Complementing yhe CMU dictionary, the preparator also uses the
LibriSpeech dictionary, which contains the words not found in the cmu
(not exhaustive list however). The LibriSpeech dictionary is available
for download at http://www.openslr.org/11/

This preparator have been tested on 'train-clean-100' and
'train-clean-360' versions of LibriSpeech

"""

import os
import re

from abkhazia.corpora.preparator.abstract_preparator import AbstractPreparator
from abkhazia.corpora.utils import list_files_with_extension, flac2wav


class LibriSpeechPreparator(AbstractPreparator):
    """Convert the LibriSpeech corpus to the abkhazia format"""
    def __init__(self, input_dir, cmu_dict_dir, librispeech_dict_dir,
                 output_dir=None, verbose=False):
        # call the AbstractPreparator __init__
        super(LibriSpeechPreparator, self).__init__(
            input_dir, output_dir, verbose)

        # init path to CMU dictionary
        if not os.path.isdir(cmu_dict_dir):
            raise IOError(
                'CMU dictionary directory does not exist: {}'
                .format(cmu_dict_dir))
        self.cmu_dict_dir = cmu_dict_dir

        # init path to LibriSpeech dictionary
        if not os.path.isdir(librispeech_dict_dir):
            raise IOError(
                'LibriSpeech dictionary directory does not exist: {}'
                .format(librispeech_dict_dir))
        self.librispeech_dict_dir = librispeech_dict_dir

    name = 'LibriSpeech'

    phones = {
        'IY': u'iː',
        'IH': u'ɪ',
        'EH': u'ɛ',
        'EY': u'eɪ',
        'AE': u'æ',
        'AA': u'ɑː',
        'AW': u'aʊ',
        'AY': u'aɪ',
        'AH': u'ʌ',
        'AO': u'ɔː',
        'OY': u'ɔɪ',
        'OW': u'oʊ',
        'UH': u'ʊ',
        'UW': u'uː',
        'ER': u'ɝ',
        'JH': u'ʤ',
        'CH': u'ʧ',
        'B': u'b',
        'D': u'd',
        'G': u'g',
        'P': u'p',
        'T': u't',
        'K': u'k',
        'S': u's',
        'SH': u'ʃ',
        'Z': u'z',
        'ZH': u'ʒ',
        'F': u'f',
        'TH': u'θ',
        'V': u'v',
        'DH': u'ð',
        'M': u'm',
        'N': u'n',
        'NG': u'ŋ',
        'L': u'l',
        'R': u'r',
        'W': u'w',
        'Y': u'j',
        'HH': u'h',
    }

    silences = [u"NSN"]  # SPN and SIL will be added automatically

    variants = []  # could use lexical stress variants...

    def link_wavs(self):
        for flac in list_files_with_extension(self.input_dir, '.flac'):
            # get the wav name
            utt_id = os.path.basename(flac).replace('.flac, ')
            speaker_id = utt_id.split('-')[0]

            if len(speaker_id) == 2:
                wav = '00' + utt_id
            elif len(speaker_id) == 3:
                wav = '0' + utt_id
            else:
                wav = utt_id

            # convert original flac to renamed wav
            flac2wav(flac, os.path.join(self.wavs_dir, wav))
        print('finished linking wav files')


    def make_segment(self):
        with open(self.segments_file, 'w') as outfile:
            for wav_file in list_files_with_extension(self.wavs_dir, '.wav'):
                bname = os.path.basename(wav_file)
                utt_id = bname.replace('.wav', '')
                outfile.write(utt_id + ' ' + bname + '\n')
        print('finished creating segments file')

    def make_speaker(self):
        with open(self.speaker_file, 'w') as outfile:
            for wav in list_files_with_extension(self.wavs_dir, '.wav'):
                bname = os.path.basename(wav)
                utt_id = bname.replace('.wav', '')
                speaker_id = bname.split("-")[0]
                outfile.write(utt_id + ' ' + speaker_id + '\n')
        print('finished creating utt2spk file')

    def make_transcription(self):
        corrupted_wavs = os.path.join(self.logs_dir, 'corrupted_wavs.txt')

        outfile = open(self.transcription_file, "w")
        outfile2 = open(corrupted_wavs, "w")

        wav_list = [os.path.basename(w).replace('.wav', '') for w in
                    list_files_with_extension(self.wavs_dir, '.wav')]

        for trs_file in list_files_with_extension(self.input_dir, '.trans.txt'):
            # for each line of transcript, convert the utt_ID to
            # normalize speaker_ID and check if wav file exists; if
            # not, output corrputed files to corrupted_wavs.txt, else
            # output text.txt
            for line in open(trs_file):
                matched = re.match(r'([0-9\-]+)\s([A-Z].*)', line)
                if matched:
                    utt_id = matched.group(1)
                    speaker_id = utt_id.split("-")[0]
                    utt = matched.group(2)

                    # TODO refactor with a switch case and an aux function
                    if len(speaker_id) == 2:
                        new_utt_id = "00" + utt_id
                        if new_utt_id in wav_list:
                            outfile.write(new_utt_id + ' ' + utt + '\n')
                        else:
                            outfile2.write(new_utt_id + '.wav\n')
                    elif len(speaker_id) == 3:
                        new_utt_id = "0" + utt_id
                        if new_utt_id in wav_list:
                            outfile.write(new_utt_id + ' ' + utt + '\n')
                        else:
                            outfile2.write(new_utt_id + '.wav\n')
                    else:
                        if utt_id in wav_list:
                            outfile.write(utt_id + ' ' + utt + '\n')
                        else:
                            outfile2.write(utt_id + '.wav\n')

        print('finished creating text file')

    def make_lexicon(self):
        libridict = os.path.join(
            self.librispeech_dict_dir, 'librispeech-lexicon.txt')

        cmudict = os.path.join(
            self.cmu_dict_dir, 'cmudict.0.7a')

        outfile = open(self.lexicon_file, "w")
        # To generate the lexicon, we will use the cmu dict and the
        # dict of OOVs generated by LibriSpeech)
        infile = open(libridict, 'r')
        infile2 = open(cmudict, 'r')
        cmu_combined = {}
        for line in infile:
            if not re.match(";;; ", line):
                dictionary = re.match("(.*)\t(.*)", line)
                if dictionary:
                    entry = dictionary.group(1)
                    phn = dictionary.group(2)
                    # remove pronunciation variants
                    phn = phn.replace("0", "")
                    phn = phn.replace("1", "")
                    phn = phn.replace("2", "")
                    # create the combined dictionary
                    cmu_combined[entry] = phn

        for line in infile2:
            if not re.match(";;; ", line):
                dictionary = re.match(r"(.*)\s\s(.*)", line)
                if dictionary:
                    entry = dictionary.group(1)
                    phn = dictionary.group(2)
                    # remove pronunciation variants
                    phn = phn.replace("0", "")
                    phn = phn.replace("1", "")
                    phn = phn.replace("2", "")
                    # create the combined dictionary
                    cmu_combined[entry] = phn
        infile.close()
        infile2.close()

        # Loop through the words in transcripts by descending
        # frequency and create the lexicon by looking up in the
        # combined dictionary. If still OOV, output to OOV.txt
        for w, f in sorted(cmu_combined.items()):
            outfile.write(w + ' ' + f + '\n')
        print('finished creating lexicon file')
        outfile.close()
