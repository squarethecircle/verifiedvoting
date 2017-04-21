from flask import Flask
from flask import render_template
from flask import request
from flask import session
import numpy

import os
from RedisSession import RedisSessionInterface

# using this version which has code at bottom commented out to speed things up
import genvote_copy as genvote

import uuid
from itertools import chain
from petlib.bn import Bn
from petlib.ec import EcGroup, EcPt


app = Flask(__name__)
app.secret_key = "should be more secret than this" # OBVIOUSLY NEEDS TO CHANGE

# app.session_interface = RedisSessionInterface()

# written because of a weird bug where a dictionary persisted in session had its keys switch from ints to unicode
def convert_keys_to_int(d):

	new_d = {}
	for k,v in d.items():
		new_d[int(k)] = v

	return new_d

def reset_dict_keys():
	session["rev_d"] = convert_keys_to_int(session["rev_d"])
	session["challenges"] = convert_keys_to_int(session["challenges"])

# based on serializeEcPts
def serializeBns(d):
	iteror = None
	new_d = None
	if isinstance(d, Bn):
		return hex(d)
	elif isinstance(d, dict):
		new_d = dict(d)
		iteror = new_d.items()
	elif isinstance(d, list):
		new_d = list(d)
		iteror = enumerate(new_d)
	else:
		return d
	for key, value in iteror:
		if isinstance(value, Bn):
			new_d[key] = serializeBns(value)
		elif isinstance(value, dict):
			new_d[key] = serializeBns(value)
		elif isinstance(value, list):
			new_d[key] = list(map(serializeBns, value))
		elif isinstance(value, tuple):
			new_d[key] = tuple(map(serializeBns, value))
	return new_d


# serialize these Bn and EctPt -based objects before putting them in session
def persist_tricky_objects(R = None, rc = None, masks = None, rb = None, commitments = None,
	randoms = None, cmt_list = None, everything = None, rx = None, x = None, answers = None, receipt = None):

	session["R"] = serializeBns(R)
	
	session["rc"] = genvote.EcPtToStr(rc)

	session["masks"] = genvote.serializeEcPts(masks)

	session["rb"] = serializeBns(rb)

	session["commitments"] = genvote.serializeEcPts(commitments)

	session["randoms"] = serializeBns(randoms)

	session["cmt_list"] = genvote.serializeEcPts(cmt_list)

	session["everything"] = everything

	session["rx"] = serializeBns(rx)

	session["x"] = genvote.EcPtToStr(x)

	# THIS ISN'T CORRECT YET!
	print("answers: ", type(answers))
	session["answers"] = answers
	print("receipt: ", type(receipt))
	session["receipt"] = receipt


# convert from serialized form in session to original form
# currently, just returns objects as they appear in session!
def desist_tricky_objects():

	# weirdly, R = Bn.from_hex(session["R"]) gives a BN Error exception
	R = session["R"]
	rc = session["rc"]
	masks = session["masks"]
	rb = session["rb"]
	commitments = session["commitments"]
	randoms = session["randoms"]
	cmt_list = session["cmt_list"]
	everything = session["everything"]
	rx = session["rx"]
	x = session["x"]
	answers = session["answers"]
	receipt = session["receipt"]

	return R, rc, masks, rb, commitments, randoms, cmt_list, everything, rx, x, answers, receipt

def setup_machine():

	# election information
	# (consider either reading this from config file, 
	# allowing user to input at setup stage)
	session["d"] = {'ALICE': 1, 'BETTY': 2, 'CHARLIE': 3}
	session["rev_d"] = {v:k for k,v in session["d"].items()}
	session["candidates"] = [session["d"]['ALICE'], session["d"]['BETTY'], session["d"]['CHARLIE']]
	
	# for autogenerating challenges
	# with open('/usr/share/dict/words') as f:
	# 	session["dictionary_words"] = list(map(str.strip,f.readlines()))
	session["dictionary_words"] = ["hello", "these", "are", "challenge", "words", "which", "should", "later", "be", "replaced", "by", "a", "dictionary"]
	session["lenChallenge"] = 3

	# where votes are stored
	# gradually filled as more users use machine
	session["vote_data"] = []

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

	print ("candidates: ", session["candidates"])
	print ("rev_d: ", session["rev_d"])
	return render_template("stage1.html", candidates = session["candidates"], cand_dict = session["rev_d"])

@app.route("/stage2", methods = ["POST"])
def stage2():

	# super annoying that I have to do this
	reset_dict_keys()

	session["chosen"] = int(request.form["chosen"])

	# should never be triggered because we check in stage2.html
	# assert(session["chosen"] > 0 and session["chosen"] <= len(session["candidates"]))
	
	challenges = {i:" ".join(numpy.random.choice(session["dictionary_words"], session["lenChallenge"], replace = False)) for i in session["candidates"]}
	challenges[session["chosen"]] = None


	return render_template("stage2.html", candidates = session["candidates"], cand_dict = session["rev_d"], chosen = session["chosen"], challenges = challenges)

@app.route("/stage3", methods = ["POST"])
# @app.route("/")
def stage3():

	# super annoying that I have to do this
	reset_dict_keys()
	
	session["challenges"] = {}
	for i in session["candidates"]:
		if i != session["chosen"]:
			session["challenges"][i] = request.form["challenge" + str(i)]
		# else:
		# 	session["challenges"][i] = None
	# print(session["challenges"])

	# NEW
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


	persist_tricky_objects(R, rc, masks, rb, commitments, randoms, cmt_list, everything, rx, x, answers = None, receipt = None)

	# print(session["challenges"])
	# session["R"] = genvote.order.random()
	# session["rc"], masks, rb = genvote.genRealCommitments(session["chosen"], genvote.K, session["R"])
	# session["commitments"], session["randoms"] = genvote.genFakeCommitments(session["challenges"], genvote.K, session["chosen"], session["R"])
	# session["randoms"][session["chosen"]] = rb
	# session["commitments"][session["chosen"]] = masks
	# session["cmt_list"] = []
	# for sk in sorted(session["commitments"]):
	# 	session["cmt_list"].append(session["commitments"][sk])
	# session["everything"] = genvote.challengeHash(''.join(map(str,[session["rc"]] + list(chain(session["cmt_list"])))), genvote.K)
	# session["rx"] = genvote.order.random()
	# session["x"] = genvote.commit(Bn.from_hex(session["everything"]), session["rx"])

	# NOW WE NEED TO PRINT THE TWO LINES BEHIND THE SHIELD


	# JUST FOR TESTING WHAT THE SERIALIZATION ISSUE IS 
	# session["R"] = None
	# session["R"] = hex(session["R"])
	# print(type(session["rc"]))
	# session["rc"] = hex(session["rc"])
	# session["masks"] = None
	# session["rb"] = None
	# session["commitments"] = None
	# session["randoms"] = None
	# session["cmt_list"] = None
	# session["everything"] = None
	# session["rx"] = None
	# session["x"] = None
	# session["answers"] = None
	# # session["challenge_dict"] = None
	# session["receipt"] = None


	return render_template("stage3.html", candidates = session["candidates"], cand_dict = session["rev_d"], chosen = session["chosen"], challenges = session["challenges"])




@app.route("/stage4")
# @app.route("/")
def stage4():

	print(session["challenges"])

	# super annoying that I have to do this for some reason
	reset_dict_keys()

	print(session["challenges"])

	chosen_challenge = " ".join(numpy.random.choice(session["dictionary_words"], session["lenChallenge"], replace = False))

	return render_template("stage4.html", candidates = session["candidates"], cand_dict = session["rev_d"], chosen = session["chosen"], challenges = session["challenges"], chosen_challenge = chosen_challenge)


@app.route("/stage5", methods = ["POST"])
# @app.route("/")
def stage5():

	# super annoying that I have to do this for some reason
	reset_dict_keys()

	session["challenges"][session["chosen"]] = request.form["chosen_challenge"]



	# NEW
	R, rc, masks, rb, commitments, randoms, cmt_list, everything, rx, x, answers, receipt = desist_tricky_objects()

	answers = genvote.answerChallenges(session["challenges"], randoms, genvote.K, R)
	genvote.verifyCommitment(x, rc, cmt_list, rx)
	challenge_dict = {candidate: {'challenge': session["challenges"][candidate], 'answer': list(map(str,answers[candidate])), 'proof': commitments[candidate]} for candidate in session["challenges"]}
	receipt = genvote.serializeEcPts({'voter_id': session["voter_id"], 'challenges': challenge_dict, 'vote_commitment': rc, 'rx': str(rx), 'commitment_to_everything': x})
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
	img.save()
	img.save('qrcodes/to_print.png')
	# REALLY, WE NEED TO PRINT THE QR CODE

	persist_tricky_objects(R, rc, masks, rb, commitments, randoms, cmt_list, everything, rx, x, answers, receipt)

	return render_template("stage5.html", candidates = session["candidates"], cand_dict = session["rev_d"], chosen = session["chosen"], challenges = session["challenges"])

@app.route("/stage6")
def stage6():

	R, rc, masks, rb, commitments, randoms, cmt_list, everything, rx, x, answers, receipt = desist_tricky_objects()

	# after confirming, store voter information
	session["vote_data"].append((session["chosen"], rc, R, everything, str(x), answers, receipt))

	return render_template("stage6.html")

@app.route("/finish")
def finish():

	session["vote_data"].sort(key = lambda x: x[6]['voter_id'])
	votes = [v[0] for v in vote_data]
	vote_commits = [v[1] for v in vote_data]
	randoms = [v[2] for v in vote_data]

	receipts = [v[6] for v in vote_data]
	genvote.verifyChallenge(receipts[0]['challenges'], receipts[0]['vote_commitment'])

	tally = Counter(votes)
	print(tally)

	proofs = genvote.doFiatShamir(votes, vote_commits, randoms, tally)
	big_dict = {'G': '934', 'sleeve': genvote.sleeve, 'g': genvote.EcPtToStr(g), 'h': genvote.EcPtToStr(h), 'precinct-id': '0', 'receipts': receipts, 'tally': tally, 'proofs': proofs}
	json_str = json.dumps(big_dict)

	for candidate in tally:
		print("%s: %d" % (session["rev_d"][candidate], tally[candidate]))
	with open("./verification.json", 'w') as f:
		f.write(json_str)

	return render_template("finished.html")

if __name__ == "__main__":
    app.run(port = 5678, debug = True)