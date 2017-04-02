from flask import Flask
from flask import render_template
from flask import request
from flask import session
import numpy

app = Flask(__name__)
app.secret_key = "should be more random than this"

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

def initialize_cands():

	cands = []
	cands.append("Bertha (Blue Party)")
	cands.append("Gilbert (Green Party)")
	cands.append("Rover (Red Party)")

	return cands

@app.route("/")
def stage0():
	return render_template("stage0.html")

@app.route("/stage1")
def stage1():

	# initialize session
    session["cands"] = initialize_cands()
    session["words"] = ["hello", "these", "are", "challenge", "words", "which", "should", "later", "be", "replaced", "by", "a", "dictionary"]
    session["lenChallenge"] = 3
    session["chosen"] = None
    session["challenges"] = None
    session["chosen_challenge"] = None


    # i = Interaction(r)
    # i.start()
    return render_template("stage1.html", cands = [(i, c) for i,c in enumerate(session["cands"])])

@app.route("/stage2", methods = ["POST"])
# @app.route("/")
def stage2():
	
	session["chosen"] = int(request.form["chosen"])

	# should never be triggered because we check in stage2.html
	assert(session["chosen"] >= 0 and session["chosen"] < len(session["cands"]))
	
	challenges = {i:" ".join(numpy.random.choice(session["words"], session["lenChallenge"], replace = False)) for i,c in enumerate(session["cands"])}
	challenges[session["chosen"]] = None
	# print("I'm in stage 2")
	# print(challenges)

	return render_template("stage2.html", cands = [(i, c) for i,c in enumerate(session["cands"])], chosen = session["chosen"], challenges = challenges)

@app.route("/stage3", methods = ["POST"])
# @app.route("/")
def stage3():
	
	session["challenges"] = {}
	for i in range(0, len(session["cands"])):
		if i != session["chosen"]:
			session["challenges"][i] = request.form["challenge" + str(i)]
		else:
			session["challenges"][i] = None
	# print("I'm in stage 3")
	# print(session["challenges"])


	return render_template("stage3.html", cands = [(i, c) for i,c in enumerate(session["cands"])], chosen = session["chosen"], challenges = session["challenges"])

# written because of a weird bug where a dictionary persisted in session had its keys switch from ints to unicode
def convert_keys_to_int(d):

	new_d = {}
	for k,v in d.items():
		new_d[int(k)] = v

	return new_d


@app.route("/stage4")
# @app.route("/")
def stage4():

	
	session["challenges"] = convert_keys_to_int(session["challenges"])
	# print("I'm in stage 4")
	# print(session["challenges"])

	chosen_challenge = " ".join(numpy.random.choice(session["words"], session["lenChallenge"], replace = False))

	return render_template("stage4.html", cands = [(i, c) for i,c in enumerate(session["cands"])], chosen = session["chosen"], challenges = session["challenges"], chosen_challenge = chosen_challenge)


@app.route("/stage5", methods = ["POST"])
# @app.route("/")
def stage5():

	session["challenges"] = convert_keys_to_int(session["challenges"])
	session["challenges"][session["chosen"]] = request.form["chosen_challenge"]

	return render_template("stage5.html", cands = [(i, c) for i,c in enumerate(session["cands"])], chosen = session["chosen"], challenges = session["challenges"])

@app.route("/stage6")
def stage6():

	# store receipt to flat file

	return render_template("stage6.html")

if __name__ == "__main__":
    app.run(port = 5678, debug = True)