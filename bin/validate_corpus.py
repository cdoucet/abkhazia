# -*- coding: utf-8 -*-
"""
Created on Wed Feb  4 00:17:47 2015

@author: Thomas Schatz
"""

"""
This script checks whether a given speech corpus is correctly formatted 
for usage with abkhazia tools. 

Beware that it automatically corrects some basics problems and thus it can
modify the original files. For example it sorts the lines of some text files 
and add default values to phone inventories when they are missing.
"""

import contextlib
import utilities.log2file
import os
import wave
import codecs
import subprocess
import collections
import argparse


def cpp_sort(filename):
	# there is redundancy here but I didn't check which export can be 
	# safely removed, so better safe than sorry
	os.environ["LC_ALL"] = "C"
	subprocess.call("export LC_ALL=C; sort {0} -o {1}".format(filename, filename), shell=True, env=os.environ)


#TODO: share these functions between modules

def basic_parse(line, filename):
	# check line break
	assert not('\r' in line), "'{0}' contains non Unix-style linebreaks".format(filename)
	# check spacing
	assert not('  ' in line), "'{0}' contains lines with two consecutive spaces".format(filename)
	# remove line break
	line = line[:-1]
	# parse line
	l = line.split(" ")
	return l


def read_segments(filename):
	utt_ids, wavs, starts, stops = [], [], [], []
	with codecs.open(filename, mode='r', encoding="UTF-8") as inp:
		lines = inp.readlines()
	for line in lines:
		l = basic_parse(line, filename)
		assert(len(l) == 2 or len(l) == 4), \
			"'segments' should contain only lines with two or four columns"
		utt_ids.append(l[0])
		wavs.append(l[1])
		if len(l) == 4:
			starts.append(float(l[3]))
			stops.append(float(l[4]))
		else:
			starts.append(None)
			stops.append(None)
	return utt_ids, wavs, starts, stops


def read_utt2spk(filename):
	utt_ids, speakers = [], []
	with codecs.open(filename, mode='r', encoding="UTF-8") as inp:
		lines = inp.readlines()
	for line in lines:
		l = basic_parse(line, filename)
		assert(len(l) == 2), "'utt2spk' should contain only lines with two columns"
		utt_ids.append(l[0])
		speakers.append(l[1])
	return utt_ids, speakers


def read_text(filename):
	utt_ids, utt_words = [], []
	with codecs.open(filename, mode='r', encoding="UTF-8") as inp:
		lines = inp.readlines()
	for line in lines:
		l = basic_parse(line, filename)
		assert(len(l) >= 2), "'utt2spk' should contain only lines with two or more columns"
		utt_ids.append(l[0])
		utt_words.append(l[1:])
		if u"" in l[1:]:
			print line
	return utt_ids, utt_words


def	read_phones(filename):
	phones, ipas = [], []
	with codecs.open(filename, mode='r', encoding="UTF-8") as inp:
		lines = inp.readlines()
	for line in lines:
		l = basic_parse(line, filename)
		assert(len(l) == 2), "'phones.txt' should contain only lines with two columns"
		phones.append(l[0])
		ipas.append(l[1])
	return phones, ipas


def	read_silences(filename):
	silences = []
	with codecs.open(filename, mode='r', encoding="UTF-8") as inp:
		lines = inp.readlines()
	for line in lines:
		l = basic_parse(line, filename)
		assert(len(l) == 1), "'silences.txt' should contain only lines with one column"
		silences.append(l[0])
	return silences


def read_variants(filename):
	variants = []
	with codecs.open(filename, mode='r', encoding="UTF-8") as inp:
		lines = inp.readlines()
	for line in lines:
		l = basic_parse(line, filename)
		assert(len(l) >= 2), \
			"'extra_questions.txt' should contain only lines with two or more columns"
		variants.append(l)
	return variants


def read_dictionary(filename):
	dict_words, transcriptions = [], []
	with codecs.open(filename, mode='r', encoding="UTF-8") as inp:
		lines = inp.readlines()
	for line in lines:
		l = basic_parse(line, filename)
		assert(len(l) >= 2), "'lexicon.txt' should contain only lines with two or more columns"
		dict_words.append(l[0])
		transcriptions.append(l[1:])
	return dict_words, transcriptions


def with_default(value, default):
	return default if value is None else value


def get_duplicates(l):
	counts = collections.Counter(l)
	duplicates = [e for e in counts if counts[e] > 1]
	return duplicates

	
def strcounts2unicode(strcounts):
	return u", ".join([u"'" + s + u"': " + unicode(c) for s, c in strcounts])
		
		
def validate(corpus_path, verbose=False):

	"""
	Check corpus directory structure and set log files up
	"""
	data_dir = os.path.join(corpus_path, 'data')
	if not(os.path.isdir(data_dir)):
		raise IOError("Corpus folder {0} should contain a 'data' subfolder".format(corpus_path))
	log_dir = os.path.join(corpus_path, 'logs')
	if not(os.path.isdir(log_dir)):
		raise IOError("Corpus folder {0} should contain a 'logs' subfolder".format(corpus_path))	
	
	# log file config
	log_file = os.path.join(log_dir, "data_validation.log".format(corpus_path))
	log = utilities.log2file.get_log(log_file, verbose)

	try:
		"""
		wav directory must contain only mono wavefiles in 16KHz, 16 bit PCM format
		"""
		log.debug("Checking 'wavs' folder")
		wav_dir = os.path.join(data_dir, 'wavs')
		wavefiles = os.listdir(wav_dir)
		durations = {}
		wrong_extensions = [f for f in wavefiles if f[-4:] != ".wav"]
		if wrong_extensions:
			raise IOError(
				(
				"The following files in 'wavs' folder do "
				"not have a '.wav' extension: {0}"
				).format(wrong_extensions)
			)
		nb_channels, width, rate, nframes, comptype, compname = {}, {}, {}, {}, {}, {}
		for f in wavefiles:
			filepath = os.path.join(wav_dir, f)
			with contextlib.closing(wave.open(filepath,'r')) as fh:
				(nb_channels[f], width[f], rate[f],
				 nframes[f], comptype[f], compname[f]) = fh.getparams()
		    	durations[f] = nframes[f]/float(rate[f])
		empty_files = [f for f in wavefiles if nframes[f] == 0]
		if empty_files:
			raise IOError("The following files are empty: {0}".format(empty_files))
		weird_rates = [f for f in wavefiles if rate[f] != 16000]
		if weird_rates:
			raise IOError(
				(
				"Currently only files sampled at 16,000 Hz "
				"are supported. The following files are sampled "
				"at other frequencies: {0}"
				).format(weird_rates)
			)
		non_mono = [f for f in wavefiles if nb_channels[f] != 1]
		if non_mono:
			raise IOError(
				(
				"Currently only mono files are supported. "
				"The following files have more than "
				"one channel: {0}"
				).format(non_mono)
			)
		non_16bit = [f for f in wavefiles if width[f] != 2]  # in bytes: 16 bit == 2 bytes
		if non_16bit:  
			raise IOError(
				(
				"Currently only files encoded on 16 bits are "
				"supported. The following files are not encoded "
				"in this format: {0}"
				).format(non_16bit)
			)
		compressed = [f for f in wavefiles if comptype[f] != 'NONE']
		if compressed:
			raise IOError("The following files are compressed: {0}".format(compressed))
		log.debug("'wavs' folder is OK")


		"""
		checking utterances list
		"""
		log.debug("Checking 'segments' file")
		log.debug("C++ sort file")
		seg_file = os.path.join(data_dir, "segments")
		cpp_sort(seg_file)  # C++ sort file for convenience
		utt_ids, wavs, starts, stops = read_segments(seg_file)
		# unique utterance-ids
		duplicates = get_duplicates(utt_ids)
		if duplicates:
			raise IOError(
				(
				"The following utterance-ids in "
				"'segments' are used several times: {0}"
				).format(duplicates)
			)
		# all referenced wavs are in wav folder
		missing_wavefiles = set.difference(set(wavs), set(wavefiles))
		if missing_wavefiles:
			raise IOError(
				(
				"The following wavefiles are referenced "
				"in 'segments' but are not in wav folder: {0}"
				).format(missing_wavefiles)
			)
		if len(set(wavs)) == len(wavs) \
		and all([e is None for e in starts]) \
		and all([e is None for e in stops]):
			# simple case, with one utterance per file and no explicit timestamps provided
			# nothing else needs to be checked
			pass
		else:
			# more complicated case
			# find all utterances (plus timestamps) associated to each wavefile
			# and for each wavefile, check consistency of the timestamps of 
			# all utterances inside it
			# report progress as this can be a bit long
			n = len(wavefiles)
			next_display_prop = 0.1
			log.debug("Checked timestamps consistency for 0% of wavefiles")
			warning = False
			for i, wav in enumerate(wavefiles):
				duration = durations[wav]
				utts = [(utt, with_default(sta, 0), with_default(sto, duration)) for utt, w, sta, sto in zip(utt_ids, wavs, starts, stops) if w == wav]
				# first check that start < stop and within file duration
				for utt_id, start, stop in utts:
					assert stop >= start, \
						"Stop time for utterance {0} is lower than start time".format(utt_id)  # should it be >?
					assert 0 <= start <= duration, \
						"Start time for utterance {0} is not compatible with file duration".format(utt_id)
					assert 0 <= stop <= duration, \
						"Stop time for utterance {0} is not compatible with file duration".format(utt_id)	
				# then check if there is overlap in time between the different utterances
				# and if there is, issue a warning (not an error)
				# 1. check that no two utterances start or finish at the same time
				wav_starts = [start for _, start, _ in utts]
				counts = collections.Counter(wav_starts)
				same_start = {}
				for start in counts:
					if counts[start] > 1:
						same_start[start] = [utt for utt, sta, _ in utts if sta == start]
				wav_stops = [stop for _, _, stop in utts]
				counts = collections.Counter(wav_stops)
				same_stop = {}
				for stop in counts:
					if counts[stop] > 1:
						same_stop[stop] = [utt for utt, _, sto in utts if sto == stop]
				if same_start:
					warning = True
					log.warning(
						(
						"The following utterances start at the same time "
						"in wavefile {0}: {1}"
						).format(wav, same_start)
					)
				if same_stop:
					warning = True
					log.warning(
						(
						"The following utterances stop at the same time "
						"in wavefile {0}: {1}"
						).format(wav, same_stop)
					)
				# 2. now it suffices to check the following:
				wav_starts = list(set(wav_starts))
				wav_stops = list(set(wav_stops))
				timestamps = wav_starts + wav_stops
				timestamps.sort()
				overlapped = [utt for utt, start, stop in utts if timestamps.index(stop)-timestamps.index(start) != 1]
				if overlapped:
					warning = True
					log.warning(
						(
						"The following utterances from file {0} are "
						"overlapping in time: {1}"
						).format(wav, overlapped)
					)
				# report progress as the for loop can be a bit long
				prop = (i+1)/float(n)
				if prop >= next_display_prop:
					log.debug(
						(
						"Checked timestamps consistency for "
						"{0}% of wavefiles"
						).format(int(round(100*next_display_prop)))
					)
					next_display_prop = next_display_prop + 0.1
			if warning:
				log.info(
					(
					"Some utterances are overlapping in time, "
					"see details in log file {0}"
					).format(log_file)
				)
		
		log.debug("'segments' file is OK")

		
		"""
		checking speakers list
		"""
		log.debug("Checking 'speakers' file")
		log.debug("C++ sort file")
		spk_file = os.path.join(data_dir, "utt2spk")
		cpp_sort(spk_file)  # C++ sort file for convenience
		utt_ids_spk, speakers = read_utt2spk(spk_file)
		# same utterance-ids in segments and utt2spk
		if not(utt_ids_spk == utt_ids):
			duplicates = get_duplicates(utt_ids_spk)
			if duplicates:
				raise IOError(
					(
					"The following utterance-ids "
					"are used several times in 'utt2spk': {0}"
					).format(duplicates)
				)
			else:
				e_spk = set(utt_ids_spk)
				e_seg = set(utt_ids)
				e = set.difference(e_spk, e_seg)
				log.error("Utterances in utt2spk that are not in segments: {0}".format(e))
				e = set.difference(e_seg, e_spk)
				log.error("Utterances in segments that are not in utt2spk: {0}".format(e))			
				raise IOError(
					(
					"Utterance-ids in 'segments' and 'utt2spk' are not consistent, "
					"see details in log {0}"
					).format(log_file)
				)		
		# speaker ids must have a fixed length
		l = len(speakers[0])
		assert all([len(s) == l for s in speakers]), "All speaker-ids must have the same length"
		# each speaker id must be prefix of corresponding utterance-id
		for utt, spk in zip(utt_ids, speakers):
			assert utt[:l] == spk, "All utterance-ids must be prefixed by the corresponding speaker-id"
		log.debug("'speakers' file is OK")
		

		"""
		checking transcriptions
		"""
		log.debug("Checking 'text' file")
		log.debug("C++ sort file")
		txt_file = os.path.join(data_dir, "text")
		cpp_sort(txt_file)  # C++ sort file for convenience
		utt_ids_txt, utt_words = read_text(txt_file)
		# we will check that the words are mostly in the lexicon later
		# same utterance-ids in segments and text
		if not(utt_ids_txt == utt_ids):
			duplicates = get_duplicates(utt_ids_txt)
			if duplicates:
				raise IOError(
					(
					"The following utterance-ids "
					"are used several times in 'text': {0}"
					).format(duplicates)
				)
			else:
				e_txt = set(utt_ids_txt)
				e_seg = set(utt_ids)
				e = set.difference(e_txt, e_seg)
				log.error("Utterances in text that are not in segments: {0}".format(e))
				e = set.difference(e_seg, e_txt)
				log.error("Utterances in segments that are not in text: {0}".format(e))			
				raise IOError(
					(
					"Utterance-ids in 'segments' and 'text' are not consistent, "
					"see details in log {0}"
					).format(log_file)
				)		
		log.debug("'text' file is OK, checking for OOV items later")


		"""
		checking phone inventory
		"""
		log.debug(
			(
			"Checking phone inventory files 'phones.txt', 'silences.txt' and "
			"'extra_questions.txt'"
			)
		)
		# phones
		#TODO: check xsampa compatibility and/or compatibility with articulatory features databases of IPA
		# or just basic IPA correctness
		phon_file = os.path.join(data_dir, "phones.txt")
		phones, ipas = read_phones(phon_file)
		assert not(u"SIL" in phones), \
			(
			u"'SIL' symbol is reserved for indicating "
			u"optional silence, it cannot be used "
			u"in 'phones.txt'"
			)
		assert not(u"SPN" in phones), \
			(
			u"'SPN' symbol is reserved for indicating "
			u"vocal noise, it cannot be used "
			u"in 'phones.txt'"
			)
		duplicates = get_duplicates(phones)
		assert not(duplicates), \
			(
			u"The following phone symbols are used several times "
			u"in 'phones.txt': {0}"
			).format(duplicates)
		duplicates = get_duplicates(ipas)
		assert not(duplicates), \
			(
			u"The following IPA symbols are used several times "
			u"in 'phones.txt': {0}"
			).format(duplicates)
		# silences
		sil_file = os.path.join(data_dir, "silences.txt")
		if not(os.path.exists(sil_file)):
			log.warning(u"No silences.txt file, creating default one with 'SIL' and 'SPN'")
			with codecs.open(sil_file, mode='w', encoding="UTF-8") as out:
				out.write(u"SIL\n")
				out.write(u"SPN\n")
			sils = [u"SIL", u"SPN"]
		else:
			sils = read_silences(sil_file)
			duplicates = get_duplicates(sils)
			assert not(duplicates), \
				(
				u"The following symbols are used several times "
				u"in 'silences.txt': {0}"
				).format(duplicates)
			if not u"SIL" in sils:
				log.warning(u"Adding missing 'SIL' symbol to silences.txt")
				with codecs.open(sil_file, mode='a', encoding="UTF-8") as out:
					out.write(u"SIL\n")
				sils.append(u"SIL")
			if not u"SPN" in sils:
				log.warning(u"Adding missing 'SPN' symbol to silences.txt")
				with codecs.open(sil_file, mode='a', encoding="UTF-8") as out:
					out.write(u"SPN\n")
				sils.append(u"SPN")
			inter = set.intersection(set(sils), set(phones))
			assert not(inter), \
				(
				u"The following symbols are used in both 'phones.txt' "
				u"and 'silences.txt': {0}"
				).format(inter)
		# variants
		var_file = os.path.join(data_dir, "extra_questions.txt")
		if not(os.path.exists(var_file)):
			log.warning(u"No extra_questions.txt file, creating empty one")
			with codecs.open(var_file, mode='w', encoding="UTF-8") as out:
				pass
			variants = []
		else:	
			variants = read_variants(var_file)
			all_symbols = [symbol for group in variants for symbol in group]
			unknown_symbols = [symbol for symbol in all_symbols if not(symbol in phones) and not(symbol in sils)]
			assert not(unknown_symbols), \
				(
				u"The following symbols are present "
				u"in 'extra_questions.txt', but are "
				u"neither in 'phones.txt' nor in "
				u"'silences.txt': {0}"
				).format(unknown_symbols)
			duplicates = get_duplicates(all_symbols)
			assert not(duplicates), \
				(
				u"The following symbols are used several times "
				u"in 'extra_questions.txt': {0}"
				).format(duplicates)
		inventory = set.union(set(phones), set(sils))
		log.debug("Phone inventory files are OK")


		"""
		checking phonetic dictionary
		"""
		log.debug("Checking 'lexicon.txt' file")
		dict_file = os.path.join(data_dir, "lexicon.txt")
		dict_words, transcriptions = read_dictionary(dict_file)
		# unique word entries (alternative pronunciations are not currently supported)
		duplicates = get_duplicates(dict_words)
		assert not(duplicates), \
			(
			u"Alternative pronunciations are not currently supported. "
			u"The following words have several transcriptions "
			u"in 'lexicon.txt': {0}"
			).format(duplicates)
		# OOV item
		if not(u"<UNK>" in dict_words):
			log.warning("No '<UNK>' word in lexicon, adding one")
			with codecs.open(dict_file, mode='a', encoding="UTF-8") as out:
					out.write(u"<UNK> SPN\n")
			dict_words.append(u"<UNK>")
			transcriptions.append([u"SPN"])
		else:
			unk_transcript = transcriptions[dict_words.index(u"<UNK>")]
			assert unk_transcript == [u"SPN"], \
				(
				u"'<UNK>' word is reserved for mapping "
				u"OOV items and should always be transcribed "
				u"as 'SPN' (vocal) noise'"
				)
		# Should we log a warning for all words containing silence phones?
		# unused words
		dict_words_set = set(dict_words)
		used_words = [word for words in utt_words for word in words]
		used_word_types = set(used_words)
		used_word_counts = collections.Counter(used_words)
		used_dict_words = set.intersection(dict_words_set, used_word_types)
		log.warning(u"{0} dictionary words used out of {1}".format(len(used_dict_words), len(dict_words_set)))
		# oov words
		oov_word_types = set.difference(used_word_types, dict_words_set)
		oov_word_counts = collections.Counter({oov : used_word_counts[oov] for oov in oov_word_types})
		nb_oov_tokens = sum(oov_word_counts.values())
		nb_oov_types = len(oov_word_types)
		log.warning(u"{0} OOV word types in transcriptions out of {1} types in total".format(nb_oov_types, len(used_word_types)))				
		log.warning(u"{0} OOV word tokens in transcriptions out of {1} tokens in total".format(nb_oov_tokens, len(used_words)))
		log.debug(
			(
			u"List of OOV word types with occurences counts: {0}"
			).format(strcounts2unicode(oov_word_counts.most_common()))
		)
		# raise alarm if the proportion of oov words is too large
		# either in terms of types or tokens
		oov_proportion_types = nb_oov_types/float(len(used_word_types))
		oov_proportion_tokens = nb_oov_tokens/float(len(used_words))
		log.debug(u"Proportion of oov word types: {0}".format(oov_proportion_types))
		log.debug(u"Proportion of oov word tokens: {0}".format(oov_proportion_tokens))
		if oov_proportion_types > 0.1:
			log.info(u"More than 10 percent of word types used are Out-Of-Vocabulary items!")
		if oov_proportion_tokens > 0.1:
			log.info(u"More than 10 percent of word tokens used are Out-Of-Vocabulary items!")		
		# homophones (issue warnings only)
		str_transcripts = [u" ".join(phone_trans) for phone_trans in transcriptions]
		counts = collections.Counter(str_transcripts)
		duplicate_transcripts = collections.Counter({trans: counts[trans] for trans in counts if counts[trans] > 1})
		if duplicate_transcripts:
			log.info("There are homophones in the pronunciation dictionary")
			log.warning(
				(
				u"There are {0} phone sequences that correspond to several words "
				u"in the pronunciation dictionary"
				).format(len(duplicate_transcripts))
			)
			log.warning(
				(
				u"There are {0} word types with homophones "
				u"in the pronunciation dictionary"
				).format(sum(duplicate_transcripts.values()))
			)
			s = strcounts2unicode(duplicate_transcripts.most_common())
			log.warning(
				(
				u"List of homophonic phone sequences in 'lexicon.txt' "
				u"with number of corresponding word types: {0}"
				).format(s)
			)
			# get word types:
			#	- found in transcriptions
			#	- with at least one homophonic word type also found in transcriptions
			homophonic_sequences = duplicate_transcripts.keys()
			homophony_groups = {}
			for homo_transcript in homophonic_sequences:
				homo_group = [word for word, transcript in zip(dict_words, str_transcripts) \
							if transcript == homo_transcript and word in used_word_types]
				if len(homo_group) > 1:
					homophony_groups[homo_transcript] = homo_group
			nb_homo_types = sum([len(homo_group) for homo_group in homophony_groups.values()])
			log.warning(
				(
				u"{0} word types found in transcriptions with "
				u"at least one homophone also found in transcriptions "
				u"out of {1} word types in total"
				).format(nb_homo_types, len(used_word_types))
			)
			nb_homo_tokens = sum([sum([used_word_counts[word] for word in homo_group]) for homo_group in homophony_groups.values()])
			log.warning((u"{0} corresponding word tokens out of {1} total").format(nb_homo_tokens, len(used_words)))
			l = [", ".join([word + u": " + unicode(used_word_counts[word]) for word in group]) for group in homophony_groups.values()]
			s = "\n".join(l)
			log.warning(
				(
				u"List of groups of homophonic word types "
				u"(including only types actually found in transcriptions) "
				u"with number of occurences of each member of each group:\n{0}"
				).format(s)
			)
		# ooi phones
		used_phones = [phone for trans_phones in transcriptions for phone in trans_phones]
		ooi_phones = [phone for phone in set(used_phones) if not(phone in inventory)]
		if ooi_phones:
			raise IOError(u"Phonetic dictionary uses out-of-inventory phones: {0}".format(ooi_phones))
		# warning for unused phones
		unused_phones = set.difference(inventory, used_phones)
		if unused_phones:
			log.warning(
				(
				u"The following phones are never found "
				u"in the transcriptions: {0}"
				).format(unused_phones)
			)
		log.debug(u"'lexicon.txt' file is OK")
		
		# wrap-up		
		log.info("Corpus ready for use with abkhazia!!!")

	except (IOError, AssertionError) as e:
		log.error(e)
		raise e


if __name__ == '__main__':
	parser = argparse.ArgumentParser(description=\
		(
		"checks whether "
		"a corpus is correctly formatted for use with the abkhazia library"
		)
	)
	parser.add_argument('corpus_path', help=\
		(
		"path to the folder containing the corpus "
		"in abkhazia format"
		)
	)
	parser.add_argument('--verbose', action='store_true', help='verbose flag')
	args = parser.parse_args()
	validate(args.corpus_path, args.verbose)