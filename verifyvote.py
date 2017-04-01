from petlib.ec import EcGroup, EcPt
from petlib.bn import Bn
from hashlib import sha512
from genzkp import ZKProof, ZKEnv, ConstGen, Sec
from itertools import chain
from collections import defaultdict, Counter
import binascii
import json
import uuid
import random

G = EcGroup(934)
order = G.order()
h = G.generator()
g = order.random() * h

def commit(a, r):
	return a * h + r * g

K = 128

d = {'ALICE': 1, 'BETTY': 2, 'CHARLIE': 3}
rev_d = {v:k for k,v in d.items()}

candidates = [d['ALICE'], d['BETTY'], d['CHARLIE']]

def verifyCommitment(x, vote, commitments, rx):
	everything = challengeHash(''.join(map(str,[vote] + list(chain(commitments.values())))), K) #alphabetize this
	result = commit(Bn.from_hex(everything), rx)
	assert(result == x)

def verifyMaskedCommitments(pm_vote_commitments, comm_pairs, tally):
	permuted_votes = []
	for comm, unmask in zip(pm_vote_commitments, comm_pairs):
		permuted_votes.append(unmask[0])
		assert(comm == commit(unmask[0], Bn.from_decimal(unmask[1])))
	assert(tally == Counter(permuted_votes))

def verifyPermutation(pm_vote_commitments, vote_commits, maskers, pi):
	assert(pm_vote_commitments == [vote_commits[pi[i]] + maskers[pi[i]] * g for i in range(len(vote_commits))])

def strToEcPt(s, group):
	return EcPt.from_binary(binascii.unhexlify(s), group)

def verifyVotes(ver_d):
	print(ver_d['receipts'][0]['voter_id'])
	#verify commitments for each vote
	#for receipt in ver_d(receipts):
		#this function doesn't exist yet
	ver_d['receipts'].sort(key = lambda x: x['voter_id'])
	vote_commits = [strToEcPt(v['vote_commitment'], G) for v in ver_d['receipts']]
	print(vote_commits)
	#verify proofs
	for proof in ver_d['proofs']:
		if proof['proof_type'] == 'unmask':
			#verifyPermutation(list(map(lambda s: strToEcPt(s,G) , proof['pm_vote_commitments'].split(' '))), vote_commits, list(map(Bn.from_hex,proof['maskers'].split(' '))), list(map(int, proof['pi'].split(' '))))
			print("ok")
		elif proof['proof_type'] == 'open':
			#print(proof['comm_pairs'])
			cp_list = []
			for tk in proof['comm_pairs'].keys():
				cp_list.append((int(tk), proof['comm_pairs'][tk], G))
			verifyMaskedCommitments(list(map(lambda s: strToEcPt(s,G), proof['pm_vote_commitments'].split(' '))), cp_list, ver_d['tally'])
		else:
			print("Unrecognized proof type: " + proof('type'))




ver_dict = None
with open('./verification.json') as data_file:    
    ver_dict = json.load(data_file)

verifyVotes(ver_dict)

for candidate in tally:
	print("%s: %d" % (rev_d[candidate], tally[candidate]))






