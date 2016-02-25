#!/bin/bash -u
# Copyright 2015, 2016  Thomas Schatz
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#  http://www.apache.org/licenses/LICENSE-2.0
#
# THIS CODE IS PROVIDED *AS IS* BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, EITHER EXPRESS OR IMPLIED, INCLUDING WITHOUT LIMITATION ANY IMPLIED
# WARRANTIES OR CONDITIONS OF TITLE, FITNESS FOR A PARTICULAR PURPOSE,
# MERCHANTABLITY OR NON-INFRINGEMENT.
# See the Apache 2 License for the specific language governing permissions and
# limitations under the License.


###
#
#  Not yet tested on n-grams with n!=2 or on
#  non-word-position-dependent acoustic models
#
###


###### Parameters ######

# Name of the LM, must correspond to an existing folder in data/
# (typically created by the python script generating the recipe)
name=$1

# Should be set to true or false depending on whether the language
# model produced is destined to be used with an acoustic model trained
# with or without word position dependent variants of the phones.
# Only tested when it is true
word_position_dependent=true

# n in n-gram, only used if a LM is to be estimated from some text
# (see below). Only tested with n=2
model_order=2


###### Recipe ######

# directory containing all the info about the desired lm
in_dir=data/local/$name

# output directory
out_dir=data/$name

# tmp directory
tmp_dir=data/local/"$name"_tmp

# log file
log=data/prepare_"$name".log


[ -f cmd.sh ] && source ./cmd.sh \
  || echo "cmd.sh not found. Jobs may not execute properly."

. path.sh || { echo "Cannot source path.sh"; exit 1; }

# First need to do a prepare_lang in the desired folder to get to use
# the right "phone" or "word" lexicon irrespective of what was used as
# a lexicon in training. If word_position_dependent is true and the
# lm is at the phone level, use prepare_lang_wpdpl.sh in the local
# folder, otherwise we fall back to the original utils/prepare_lang.sh
# (some slight customizations of the script are necessary to decode
# with a phone loop language model when word position dependent phone
# variants have been trained).
if [ "$word_position_dependent" = true ]
then
    # empty phone file is used to signal if the LM is not at the word
    # but at the phone level
    if [ -f "in_dir"/phone ]
    then
	prepare_lang_exe=local/prepare_lang_wpdpl.sh
    else
	prepare_lang_exe=utils/prepare_lang.sh
    fi
else
    prepare_lang_exe=utils/prepare_lang.sh
fi

$prepare_lang_exe --position-dependent-phones $word_position_dependent \
                  $in_dir "<unk>" $tmp_dir $out_dir > $log

# here we could use a different silence_prob. I think however that
# --position-dependent-phones has to be the same as what was used for
# training (as well as the phones.txt, extra_questions.txt and
# nonsilence_phones.txt), otherwise the mapping between phones and
# acoustic state in the trained model will be lost

# Next three possibilities:
#  1 - A G.txt file is already provided in in_dir (FST grammar in text format)
#  2 - A G.arpa.gz MIT/ARPA formatted n-gram is already provided in in_dir
#  3 - A text.txt file from which to estimate a n-gram is provided in in_dir

if [ -f "$in_dir"/G.txt ]
then
    # 1 - compile the text format FST to binary format used by kaldi
    # in utils/mkgraph.sh
    fstcompile --isymbols=$out_dir/words.txt \
               --osymbols=$out_dir/words.txt \
               --keep_isymbols=false \
	       --keep_osymbols=false \
               $in_dir/G.txt > $out_dir/G.fst

    # sort G.fst for computational efficiency (I think)
    fstarcsort --sort_type=ilabel \
               $out_dir/G.fst > $out_dir/G2.fst

    mv $out_dir/G2.fst $out_dir/G.fst

elif [ -f "$in_dir"/G.arpa.gz ]
then
    # 2 - generate FST (use SRILM)
    # includes adapting the vocabulary to lexicon in out_dir
    # srilm_opts: do not use -tolower by default, since we do not
    # make assumption that lexicon has no meaningful
    # lowercase/uppercase distinctions (and it can be in unicode,
    # in which case I have no idea what lowercasing would produce)

    # format_lm_sri.sh copies stuff so we need to instantiate
    # another folder and then clean up (or we could do a custom
    # format_lm_sri.sh with $1 and $4 == $1 and no cp)
    tmp_out_dir="$out_dir"_tmp
    utils/format_lm_sri.sh --srilm_opts "-subset -prune-lowprobs -unk" \
			   $out_dir "$in_dir"/G.arpa.gz \
			   "in_dir"/lexicon.txt $tmp_out_dir
    rm -Rf $out_dir  # erases the previous content that is redundant anyway
    mv $tmp_out_dir $out_dir
else
    # 3 - generate ARPA/MIT n-gram with IRSTLM, then as in 2. train
    # (use IRSTLM) need to remove utt-id on first column of text file
    set -eu  # stop on error
    cut -d' ' -f2- < "$in_dir"/lm_text.txt > "$in_dir"/text_ready.txt
    add-start-end.sh < "$in_dir"/text_ready.txt > "$in_dir"/text_se.txt

    # k option is number of split, useful for huge text files
    build-lm.sh -i "$in_dir"/text_se.txt -n $model_order \
                -o "$in_dir"/text.ilm.gz -k 1 -s kneser-ney
    compile-lm "$in_dir"/text.ilm.gz --text=yes /dev/stdout | gzip -c > "$in_dir"/G.arpa.gz

    # clean intermediate files
    rm "$in_dir"/text_ready.txt
    rm "$in_dir"/text_se.txt
    rm "$in_dir"/text.ilm.gz

    # As in 2., generate FST
    tmp_out_dir="$out_dir"_tmp
    utils/format_lm_sri.sh --srilm_opts "-subset -prune-lowprobs -unk" \
			   $out_dir "$in_dir"/G.arpa.gz \
			   "in_dir"/lexicon.txt $tmp_out_dir
    rm -Rf $out_dir  # erases the previous content that is redundant anyway
    mv $tmp_out_dir $out_dir
fi
