# Copyright 2016 Thomas Schatz, Xuan-Nga Cao, Mathieu Bernard
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
"""Provides the CorpusMergeWavs class"""

import ConfigParser
import random
import numpy as np
import subprocess
import shlex
import os
import wave
import contextlib

from operator import itemgetter
from math import exp
from abkhazia.utils import logger, config


class CorpusMergeWavs(object):
    """A class for merging the wavs files together for each speaker,
    at the end of this class, one .wav file = one speaker. This 
    class also edits the segment to have a correction alignment, and
    wavs.
    
    
    corpus : The abkhazia corpus to filter. The corpus is assumed
      to be valid.

    log : A logging.Logger instance to send log messages

    function : A string that specifies the cutting function that
      will be used on the corpus

    plot : A boolean which, if set to true, enables the plotting
      of the speech distribution and the cutting function
    """
    def __init__(self, corpus, log=logger.null_logger(),
                 random_seed=None, prune=True):
        self.log = log
        self.prune = prune
        self.corpus = corpus

        # read utt2spk from the input corpus
        utt_ids, utt_speakers = zip(*self.corpus.utt2spk.iteritems())
        self.utts = zip(utt_ids, utt_speakers)
        self.size = len(utt_ids)
        self.speakers = set(utt_speakers)
        self.log.debug('loaded %i utterances from %i speakers',
                       self.size, len(self.speakers))

    def merge_wavs(self,corpus_dir,output_dir):
        '''Merge wav files to have 1 wav per speaker'''
        '''and modify accordingly segments to have correct'''
        ''' timestamps for each utterance'''

        spk2utts = dict()
        segments = self.corpus.segments
        wavs = self.corpus.wavs
        utt2spk = self.corpus.utt2spk
        utt2dur = self.corpus.utt2duration()
        
        # get input and output wav dir
        wav_output_dir = os.path.join(output_dir,'data/wavs')
        wav_dir = os.path.join(corpus_dir,'wavs')

        if not os.path.isdir(wav_dir):
            raise IOError('invalid corpus: not found{}'.format(wav_dir))
        if not os.path.isdir(wav_output_dir):
            os.makedirs(wav_output_dir)
        
        spk2dur = dict()
        spk2wavs = dict()
        spk2wav_dur = dict()
        
        # get utterances durations
        for spkr in self.speakers:
            spk_utts = [utt_id for utt_id, utt_speaker in self.utts if utt_speaker == spkr]
            duration = sum([utt2dur[utt_id] for utt_id in spk_utts])
            spk2dur[spkr] = duration
            spk2utts[spkr] = spk_utts
            self.log.debug('for speaker {}, total duration is {}'.format(
                            spkr,duration/60))
        
            wav_utt = [segments[utt][0] for utt in spk2utts[spkr]]
            
            # we want unique values in the list of wav :
            wav_utt = sorted(list(set(wav_utt)))
            spk2wavs[spkr] = wav_utt
        
            #first wav file in the list doesn't have an offset
            spk2wav_dur[spkr] = []
            spk2wav_dur[spkr].append(0)
            for wav in wav_utt:
                wav_name = '.'.join([wav,'wav'])
                wav_path = '/'.join([wav_dir,wav_name])
                
                # get wav stats
                with contextlib.closing(wave.open(wav_path,'r')) as wav_file:
                    frames = wav_file.getnframes()
                    rate = wav_file.getframerate()
                    duration = frames / float(rate)
                    self.log.debug('wav file {wav} has a duration of {dur}'.format(
                            wav=wav_name,dur=duration))
        
                spk2wav_dur[spkr].append(duration)
        
            spk2wav_dur[spkr] = np.cumsum(spk2wav_dur[spkr])
            
        
        
            #update segments
            for utt in spk2utts[spkr]:
                utt_wav_id = segments[utt][0]
                spk2wav_dur_temp = spk2wav_dur[spkr][0:len(spk2wavs[spkr])]
                wav_dur_dict = dict(zip(spk2wavs[spkr],spk2wav_dur_temp))
                offset = wav_dur_dict[utt_wav_id]
                finale_wav_id = spkr
        
                if segments[utt][1] is not None:
                    start = segments[utt][1]
                    stop = segments[utt][2]
                else:
                    # if the corpus has 1 wav file per utt, segments.txt
                    # doesn't list the timestamps.
                    start = 0
                    stop = utt2dur[utt]
                   
                segments[utt] = finale_wav_id, start + offset, stop + offset
                #the name of the finale wave file will be spkr.wav (ex s01.wav)
                  
        # update corpus values 
        self.corpus.segments = segments
        
        #merge the wavs 
        spk2list_wav_to_merge = dict() 
        for spkr in self.speakers:
            
            # create the list of waves we want to merge
            wav_name = '.'.join([spkr,'wav'])
            wav_out_path = '/'.join([wav_output_dir,wav_name])
            list_wav_to_merge = []
        
            for wav in spk2wavs[spkr]:
                wav_to_merge = '.'.join([wav, 'wav'])
                wav_to_merge = '/'.join([wav_dir, wav_to_merge])
                list_wav_to_merge.append(wav_to_merge)
            
            # create the output wave
            spk2list_wav_to_merge[spkr]=list_wav_to_merge
            data=[]
            for wav_file in spk2list_wav_to_merge[spkr]:
                wav_to_merge = wave.open(wav_file, 'rb')
                self.log.debug('for speaker {spkr} adding the wave {wav}'.format(
                        spkr=spkr, wav=wav_file))
                data.append(
                        [wav_to_merge.getparams(),
                         wav_to_merge.readframes(wav_to_merge.getnframes())])
                wav_to_merge.close
            output_wave = wave.open(wav_out_path, 'wb')
            output_wave.setparams(data[0][0])
            for nb in range(len(spk2wavs[spkr])):
                output_wave.writeframes(data[nb][1])
        
            output_wave.close()
        
        #verify that the merger worked and update wave set
        for spkr in self.speakers:
            wav_name = '.'.join([spkr, 'wav'])
            wav_out_path = '/'.join([wav_output_dir, wav_name])
        
        
            self.corpus.wavs[spkr] = wav_out_path
            if os.path.isfile(wav_out_path):
                duration = 0
                with contextlib.closing(wave.open(wav_out_path, 'r')) as f:
                    frames = f.getnframes()
                    rate = f.getframerate()
                    duration = frames/float(rate)
        
                # check if the length of the output is the sum of the wave files lengths
                if not duration<spk2wav_dur[spkr][-1] + (1.0/16000) \
                        or not  duration>spk2wav_dur[spkr][-1] - (1.0/16000):
                    self.log.debug('sum of lengths : {dur}, output length : {out}'.format(
                            dur=spk2wav_dur[spkr][-1], out=duration))
                    raise IOError(
                            '''the merged wave length is different'''
                            '''from the sum of the initial wave file''')
                    
        # validate the corpus
        self.corpus.validate()
        