from flask import Flask
from flask import render_template
from flask import request
from flask import session
import numpy

app = Flask(__name__)
app.secret_key = "should be more secret than this"

# class Candidate:
# 	def __init__(self, name, party, office):
# 		self.name = name
# 		self.party = party
# 		self.office = office

# 		# this should probably be a hash of name, party, office, or something
# 		self.candID = 1

# 	def print_name(self):
# 		return self.name + " (" + self.party + ")"

# class Race:
# 	def __init__(self, office):
# 		self.office = office

# 		# this should probably be a hash of office, or something
# 		self.raceID = 1
# 		self.cands = []

# 	def add_cand(self, name, party):
# 		self.cands.append(Candidate(name,party, self.office))
 
# def initialize_race():
	
#     r = Race("pres")
#     r.add_cand("Bertha", "Blue Party")
#     r.add_cand("Gilbert", "Green")
#     r.add_cand("Rover", "Red")
#     return r	

# written because of a weird bug where a dictionary persisted in session had its keys switch from ints to unicode
def convert_keys_to_int(d):

	new_d = {}
	for k,v in d.items():
		new_d[int(k)] = v

	return new_d
def reset_dict_keys():
	session["rev_d"] = convert_keys_to_int(session["rev_d"])
	session["challenges"] = convert_keys_to_int(session["challenges"])

def initialize():

	# cands = []
	# cands.append("Bertha (Blue Party)")
	# cands.append("Gilbert (Green Party)")
	# cands.append("Rover (Red Party)")

	# cands = {'ALICE': 1, 'BETTY': 2, 'CHARLIE': 3}

	session["d"] = {'ALICE': 1, 'BETTY': 2, 'CHARLIE': 3}
	session["rev_d"] = {v:k for k,v in session["d"].items()}
	session["candidates"] = [session["d"]['ALICE'], session["d"]['BETTY'], session["d"]['CHARLIE']]

	# with open('/usr/share/dict/words') as f:
	# 	session["dictionary_words"] = list(map(str.strip,f.readlines()))

	session["dictionary_words"] = ["hello", "these", "are", "challenge", "words", "which", "should", "later", "be", "replaced", "by", "a", "dictionary"]

	session["lenChallenge"] = 3
	session["chosen"] = None
	session["challenges"] = {}
	session["chosen_challenge"] = None

@app.route("/")
def stage0():
	return render_template("stage0.html")

@app.route("/stage1")
def stage1():

	# initialize session
    
    # session["words"] = ["hello", "these", "are", "challenge", "words", "which", "should", "later", "be", "replaced", "by", "a", "dictionary"]
    # session["lenChallenge"] = 3
    # session["chosen"] = None
    # session["challenges"] = None
    # session["chosen_challenge"] = None


    initialize()

    # i = Interaction(r)
    # i.start()
    return render_template("stage1.html", candidates = session["candidates"], cand_dict = session["rev_d"])

@app.route("/stage2", methods = ["POST"])
# @app.route("/")
def stage2():
	

	# super annoying that I have to do this for some reason
	reset_dict_keys()

	session["chosen"] = int(request.form["chosen"])

	# should never be triggered because we check in stage2.html
	assert(session["chosen"] > 0 and session["chosen"] <= len(session["candidates"]))
	
	challenges = {i:" ".join(numpy.random.choice(session["dictionary_words"], session["lenChallenge"], replace = False)) for i in session["candidates"]}
	challenges[session["chosen"]] = None
	# print("I'm in stage 2")
	# print(challenges)


	return render_template("stage2.html", candidates = session["candidates"], cand_dict = session["rev_d"], chosen = session["chosen"], challenges = challenges)

@app.route("/stage3", methods = ["POST"])
# @app.route("/")
def stage3():

	# super annoying that I have to do this for some reason
	reset_dict_keys()
	
	session["challenges"] = {}
	for i in session["candidates"]:
		if i != session["chosen"]:
			session["challenges"][i] = request.form["challenge" + str(i)]
		else:
			session["challenges"][i] = None
	# print("I'm in stage 3")
	# print(session["challenges"])


	

	return render_template("stage3.html", candidates = session["candidates"], cand_dict = session["rev_d"], chosen = session["chosen"], challenges = session["challenges"])




@app.route("/stage4")
# @app.route("/")
def stage4():

	# super annoying that I have to do this for some reason
	reset_dict_keys()
	# print("I'm in stage 4")
	# print(session["challenges"])

	chosen_challenge = " ".join(numpy.random.choice(session["dictionary_words"], session["lenChallenge"], replace = False))

	return render_template("stage4.html", candidates = session["candidates"], cand_dict = session["rev_d"], chosen = session["chosen"], challenges = session["challenges"], chosen_challenge = chosen_challenge)


@app.route("/stage5", methods = ["POST"])
# @app.route("/")
def stage5():

	# super annoying that I have to do this for some reason
	reset_dict_keys()


	session["challenges"][session["chosen"]] = request.form["chosen_challenge"]

	return render_template("stage5.html", candidates = session["candidates"], cand_dict = session["rev_d"], chosen = session["chosen"], challenges = session["challenges"])

@app.route("/stage6")
def stage6():

	# store receipt to flat file

	return render_template("stage6.html")

if __name__ == "__main__":
    app.run(port = 5678, debug = True)