from flask import Flask
from flask import render_template
from flask import request
from flask import session
# import numpy
import os
import re
import random

import os
from RedisSession import RedisSessionInterface

# using this version which has code at bottom commented out to speed things up
import genvote_interface as genvote

import uuid
from itertools import chain
from petlib.bn import Bn
from petlib.ec import EcGroup, EcPt
from petlib.pack import encode, decode
from petlib.ecdsa import do_ecdsa_sign, do_ecdsa_setup
import qrcode
from collections import defaultdict, Counter
import json

import requests
# from bs4 import BeautifulSoup


app = Flask(__name__)
app.secret_key = "should be more secret than this" # OBVIOUSLY NEEDS TO CHANGE

app.session_interface = RedisSessionInterface()

# written because of a weird bug where a dictionary persisted in session had its keys switch from ints to unicode
def convert_keys_to_int(d):
	new_d = {}
	for k,v in d.items():
		new_d[int(k)] = v
	return new_d
def reset_dict_keys():
	session["rev_d"] = convert_keys_to_int(session["rev_d"])
	session["challenges"] = convert_keys_to_int(session["challenges"])

def print_image(imgurl):
	os.system('lpr -o fit-to-page ' + imgurl)

def print_text(text_tp):
	#os.system('echo -e "' + text_tp + '\\n\\n\\n" > /dev/ttyAMA0')
	os.system('echo "' + text_tp + '" | lpr')

# MADE OBSOLETE BY PETLIB.PACK ENCODE/DECODE
# # based on serializeEcPts
# def serializeBns(d):
# 	iteror = None
# 	new_d = None
# 	if isinstance(d, Bn):
# 		return hex(d)
# 	elif isinstance(d, dict):
# 		new_d = dict(d)
# 		iteror = new_d.items()
# 	elif isinstance(d, list):
# 		new_d = list(d)
# 		iteror = enumerate(new_d)
# 	else:
# 		return d
# 	for key, value in iteror:
# 		if isinstance(value, Bn):
# 			new_d[key] = serializeBns(value)
# 		elif isinstance(value, dict):
# 			new_d[key] = serializeBns(value)
# 		elif isinstance(value, list):
# 			new_d[key] = list(map(serializeBns, value))
# 		elif isinstance(value, tuple):
# 			new_d[key] = tuple(map(serializeBns, value))
# 	return new_d

# need this because can't serialize vote_data
def append_vote_data(vd):
	vote_data = decode (session["vote_data"])
	vote_data.append(vd)
	session["vote_data"] = encode (vote_data)

# serialize these Bn and EctPt -based objects before putting them in session
def persist_tricky_objects(R = None, rc = None, masks = None, rb = None, commitments = None,
	randoms = None, cmt_list = None, everything = None, rx = None, x = None, answers = None, receipt = None):

	# print ("SERIALIZING STUFF!")

	# print("R: ", type(R), type(encode(R)))
	session["R"] = encode(R)

	# print("rc: ", type(rc), type(encode(rc)))
	session["rc"] = encode(rc)

	# print("masks: ", type(masks), type(encode(masks)))
	session["masks"] = encode(masks)

	# print("rb: ", type(rb), type(encode(rb)))
	session["rb"] = encode(rb)

	# print("commitments: ", type(commitments), type(encode(commitments)))
	session["commitments"] = encode(commitments)

	# print("randoms: ", type(randoms), type(encode(randoms)))
	session["randoms"] = encode(randoms)

	# print("cmt_list: ", type(cmt_list), type(encode(cmt_list)))
	session["cmt_list"] = encode(cmt_list)

	# i think this is fine as is
	# print("everything", type(everything))
	session["everything"] = everything

	# print("rx: ", type(rx), type(encode(rx)))
	session["rx"] = encode(rx)

	# print("x: ", type(x), type(encode(x)))
	session["x"] = encode(x)

	# print("answers: ", type(answers))
	session["answers"] = encode(answers)
	# print("receipt: ", type(receipt))
	session["receipt"] = encode(receipt)


# convert from serialized form in session to original form
# currently, just returns objects as they appear in session!
def desist_tricky_objects():

	# print ("deSERIALIZING STUFF!")

	# weirdly, R = Bn.from_hex(session["R"]) gives a BN Error exception
	
	R = decode(session["R"])
	# print("R: ", type(session["R"]), type(R))
	
	rc = decode(session["rc"])
	# print("rc: ", type(session["rc"]), type(rc))
	
	masks = decode(session["masks"])
	# print("masks: ", type(session["masks"]), type(masks))
	
	rb = decode(session["rb"])
	# print("rb: ", type(session["rb"]), type(rb))

	commitments = decode(session["commitments"])
	# print("commitments: ", type(session["commitments"]), type(commitments))

	randoms = decode(session["randoms"])
	# print("randoms: ", type(session["randoms"]), type(randoms))

	cmt_list = decode(session["cmt_list"])
	# print("cmt_list: ", type(session["cmt_list"]), type(cmt_list))

	everything = session["everything"]
	# print("everything: ", type(session["everything"]), type(everything))

	rx = decode(session["rx"])
	# print("rx: ", type(session["rx"]), type(rx))

	x = decode(session["x"])
	# print("x: ", type(session["x"]), type(x))

	answers = decode(session["answers"])

	receipt = decode(session["receipt"])

	return R, rc, masks, rb, commitments, randoms, cmt_list, everything, rx, x, answers, receipt

def setup_machine():
	# set serial baud
	os.system('stty -F /dev/ttyAMA0 19200')
	# election information
	# (consider either reading this from config file, 
	# allowing user to input at setup stage)
	session["d"] = {'ALICE': 1, 'BETTY': 2, 'CHARLIE': 3}
	session["rev_d"] = {v:k for k,v in session["d"].items()}
	session["candidates"] = [session["d"]['ALICE'], session["d"]['BETTY'], session["d"]['CHARLIE']]
	
	# for autogenerating challenges
	# with open('/usr/share/dict/words') as f:
	# 	session["dictionary_words"] = list(map(str.strip,f.readlines()))
	# session["dictionary_words"] = ["hello", "these", "are", "challenge", "words", "which", "should", "later", "be", "replaced", "by", "a", "dictionary"]
	
	# from https://github.com/first20hours/google-10000-english
	# (google-10000-english-usa-no-swears.txt)
	# with stopwords removed using nltk
	with open('interface_words.txt','r') as iw:
		words = iw.readlines()

	# http://stackoverflow.com/questions/3277503/how-do-i-read-a-file-line-by-line-into-a-list
	words = [w.strip() for w in words]
	session["dictionary_words"] = words


	session["lenChallenge"] = 3

	# where votes are stored
	# gradually filled as more users use machine
	# needs to be encoded because will contain material that will need to be encoded
	session["vote_data"] = encode([])

# values that should be refreshed every time there is a new voter
def new_voter():

	session["voter_id"] = str(uuid.uuid4())
	session["chosen"] = None
	session["challenges"] = {}
	session["chosen_challenge"] = None

	# new variables from castVote
	# using session["chosen"] instead of candidate, and session["challenges"] instead of DC

	# calling this with no arguments should set all the rest of the variables we need to persist to None
	persist_tricky_objects()

	# NOW TAKEN CARE OF IN PERSIST_TRICKY_OBJECTS
	# session["R"] = None
	# session["rc"] = None
	# session["masks"] = None
	# session["rb"] = None
	# session["commitments"] = None
	# session["randoms"] = None
	# session["cmt_list"] = None
	# session["everything"] = None
	# session["rx"] = None
	# session["x"] = None
	# session["answers"] = None
	# session["receipt"] = None

	# DO NOT NEED TO BE PERSISTED ACROSS VIEWS
	# session["challenge_dict"] = None
	# session["sig"] = None
	# session["signed_cmt"] = None
	# session["qr"] = None
	# session["img"] = None

@app.route("/")
def start_machine():

	setup_machine()

	return render_template("setup.html")

@app.route("/stage0")
def stage0():

	new_voter()

	return render_template("stage0.html", voter_id = session["voter_id"])

@app.route("/stage1")
def stage1():

	reset_dict_keys()

	# print ("candidates: ", session["candidates"])
	# print ("rev_d: ", session["rev_d"])
	return render_template("stage1.html", candidates = session["candidates"], cand_dict = session["rev_d"], voter_id = session["voter_id"])

@app.route("/stage2", methods = ["POST"])
def stage2():

	# super annoying that I have to do this
	reset_dict_keys()

	session["chosen"] = int(request.form["chosen"])

	# should never be triggered because we check in stage2.html
	# assert(session["chosen"] > 0 and session["chosen"] <= len(session["candidates"]))
	
	# challenges = {i:" ".join(numpy.random.choice(session["dictionary_words"], session["lenChallenge"], replace = False)) for i in session["candidates"]}
	challenges = {i:" ".join(random.sample(session["dictionary_words"], session["lenChallenge"])) for i in session["candidates"]}
	challenges[session["chosen"]] = None


	return render_template("stage2.html", candidates = session["candidates"], cand_dict = session["rev_d"], chosen = session["chosen"], challenges = challenges, voter_id = session["voter_id"])

@app.route("/stage3", methods = ["POST"])
# @app.route("/")
def stage3():

	# super annoying that gI have to do this
	reset_dict_keys()
	
	session["challenges"] = {}
	for i in session["candidates"]:
		if i != session["chosen"]:
			session["challenges"][i] = request.form["challenge" + str(i)]
		# else:
		# 	session["challenges"][i] = None
	# print(session["challenges"])

	R = genvote.order.random()
	rc, masks, rb = genvote.genRealCommitments(session["chosen"], genvote.K, R)
	commitments, randoms = genvote.genFakeCommitments(session["challenges"], genvote.K, session["chosen"], R)
	randoms[session["chosen"]] = rb
	commitments[session["chosen"]] = masks
	cmt_list = []
	for sk in sorted(commitments):
		cmt_list.append(commitments[sk])
	everything = genvote.challengeHash(''.join(map(str,[rc] + list(chain(cmt_list)))), genvote.K)
	rx = genvote.order.random()
	x = genvote.commit(Bn.from_hex(everything), rx)


	# print("gCHECKING THAT ENCODE AND DECODE WORK!")
	# eR = encode(R)
	# ueR = decode(eR)
	# print("R: ", type(R), type(eR), type(ueR), R == ueR)


	persist_tricky_objects(R, rc, masks, rb, commitments, randoms, cmt_list, everything, rx, x, answers = None, receipt = None)

	# NOW WE NEED TO PRINT THE TWO LINES BEHIND THE SHIELD
	#os.system('echo "' + genvote.EcPtToStr(x) + '" | lpr')
	print_text(genvote.EcPtToStr(x))

	return render_template("stage3.html", candidates = session["candidates"], cand_dict = session["rev_d"], chosen = session["chosen"], challenges = session["challenges"], voter_id = session["voter_id"])




@app.route("/stage4")
# @app.route("/")
def stage4():

	# print(session["challenges"])

	# super annoying that I have to do this for some reason
	reset_dict_keys()

	# print(session["challenges"])

	# chosen_challenge = " ".join(numpy.random.choice(session["dictionary_words"], session["lenChallenge"], replace = False))
	chosen_challenge = " ".join(random.sample(session["dictionary_words"], session["lenChallenge"]))

	return render_template("stage4.html", candidates = session["candidates"], cand_dict = session["rev_d"], chosen = session["chosen"], challenges = session["challenges"], chosen_challenge = chosen_challenge, voter_id = session["voter_id"])


@app.route("/stage5", methods = ["POST"])
# @app.route("/")
def stage5():

	# super annoying that I have to do this for some reason
	reset_dict_keys()

	session["challenges"][session["chosen"]] = request.form["chosen_challenge"]



	R, rc, masks, rb, commitments, randoms, cmt_list, everything, rx, x, answers, receipt = desist_tricky_objects()

	answers = genvote.answerChallenges(session["challenges"], randoms, genvote.K, R)
	# genvote.verifyCommitment(x, rc, cmt_list, rx)
	challenge_dict = {candidate: {'challenge': session["challenges"][candidate], 'answer': list(map(str,answers[candidate])), 'proof': commitments[candidate]} for candidate in session["challenges"]}
	receipt = genvote.serializeEcPts({'voter_id': session["voter_id"], 'challenges': challenge_dict, 'vote_commitment': rc, 'rx': str(rx), 'commitment_to_everything': x})
	
	# random beacon
	r = requests.get("https://beacon.nist.gov/rest/record/last")
	timestamp = re.search(r"<timeStamp>(.*)<\/timeStamp>",r.text).group(1)
	outputvalue = re.search(r"<outputValue>(.*)<\/outputValue>",r.text).group(1)
	# timestamp and outputvalue need to be printed to receipt in some way
	# print(timestamp, outputvalue)

	sig = do_ecdsa_sign(genvote.G, genvote.sig_key, genvote.EcPtToStr(x).encode('utf-8'), genvote.kinv_rp)
	signed_cmt = ' '.join((genvote.EcPtToStr(x), hex(sig[0])[2:], hex(sig[1])[2:]))
	qr = qrcode.QRCode(
			version = 1,
			error_correction = qrcode.constants.ERROR_CORRECT_L,
			box_size = 4,
			border = 4,
	)
	qr.add_data(signed_cmt)
	qr.make()
	img = qr.make_image()
	qr_path = 'qrcodes/' + session["voter_id"] + '.png'
	img.save(qr_path)
	# REALLY, WE NEED TO PRINT THE QR CODE HERE, NOT SAVE IT
	#os.system('echo "Signed Commitment: ' + signed_cmt + '" | lpr')
	# print qr code
	#os.system('lpr -o fit-to-page ' + qr_path)
	print_image(qr_path)
	# print voter_id
	#os.system('echo "Voter ID: ' + session["voter_id"] + '" | lpr')
	print_text('Voter ID: ' + session["voter_id"])
	# print Receipt Certified
	#os.system('echo "--RECEIPT CERTIFIED--" | lpr')
	print_text('------RECEIPT CERTIFIED------')

	persist_tricky_objects(R, rc, masks, rb, commitments, randoms, cmt_list, everything, rx, x, answers, receipt)

	return render_template("stage5.html", candidates = session["candidates"], cand_dict = session["rev_d"], chosen = session["chosen"], challenges = session["challenges"], voter_id = session["voter_id"])

@app.route("/stage6")
def stage6():

	R, rc, masks, rb, commitments, randoms, cmt_list, everything, rx, x, answers, receipt = desist_tricky_objects()

	# after confirming, store voter information
	append_vote_data((session["chosen"], rc, R, everything, str(x), answers, receipt))

	return render_template("stage6.html")

@app.route("/finish")
def finish():

	vote_data = decode(session["vote_data"])
	vote_data.sort(key = lambda x: x[6]['voter_id'])
	votes = [v[0] for v in vote_data]
	vote_commits = [v[1] for v in vote_data]
	randoms = [v[2] for v in vote_data]

	receipts = [v[6] for v in vote_data]
	# genvote.verifyChallenge(receipts[0]['challenges'], receipts[0]['vote_commitment'])

	tally = Counter(votes)
	print(tally)

	proofs = genvote.doFiatShamir(votes, vote_commits, randoms, tally)
	big_dict = {'G': '934', 'sleeve': genvote.sleeve, 'g': genvote.EcPtToStr(genvote.g), 'h': genvote.EcPtToStr(genvote.h), 'precinct-id': '0', 'receipts': receipts, 'tally': tally, 'proofs': proofs}
	json_str = json.dumps(big_dict)

	for candidate in tally:
		print("%s: %d" % (session["rev_d"][candidate], tally[candidate]))
	with open("./verification.json", 'w') as f:
		f.write(json_str)

	return render_template("finished.html")

if __name__ == "__main__":
    app.run(port = 5678, debug = True)