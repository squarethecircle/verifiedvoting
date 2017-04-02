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


#order = G.order()
#h = G.generator()
#g = order.random() * h

def commit(a, r, h, g):
	return a * h + r * g

K = 128

d = {'ALICE': 1, 'BETTY': 2, 'CHARLIE': 3}
rev_d = {v:k for k,v in d.items()}

candidates = [d['ALICE'], d['BETTY'], d['CHARLIE']]

def verifyMaskedCommitments(pm_vote_commitments, comm_pairs, tally, h, g):
	permuted_votes = []
	for comm, unmask in zip(pm_vote_commitments, comm_pairs):
		permuted_votes.append(unmask[0])
		assert(comm == commit(unmask[0], Bn.from_decimal(unmask[1]), h, g))
	assert({str(k): v for k, v in Counter(permuted_votes).items()} == tally)

def verifyPermutation(pm_vote_commitments, vote_commits, maskers, pi, g):
	assert(pm_vote_commitments == [vote_commits[pi[i]] + maskers[pi[i]] * g for i in range(len(vote_commits))])

def challengeHash(challenge, k):
	assert(k <= 512)
	m = sha512(challenge.encode('utf-8')).hexdigest()
	nbytes = k // 8
	nbits = k % 8
	byte_trunc_m = m[:2*nbytes]
	if nbits > 0:
		bit_trunc_m = m[2*nbytes: 2*nbytes + 2]
		bit_num = (int(bit_trunc_m, 16) >> (8 - nbits)) << (8 - nbits)
		byte_trunc_m += format(bit_num, 'x')
	return byte_trunc_m

def verifyChallenge(cd, vote_commitment, G, h, g):
	vc = strToEcPt(vote_commitment, G)
	for candidate in cd:
		answers = list(map(Bn.from_decimal,cd[candidate]['answer']))
		proofs = list(map(lambda l: strToEcPt(l, G), cd[candidate]['proof']))
		challenge_bits = int(challengeHash(cd[candidate]['challenge'], K), 16)
		for i in range(K):
			if (challenge_bits & 1) == 0:
				assert(proofs[i] == commit(int(candidate), answers[i], h, g))
			else:
				assert(proofs[i] == vc + answers[i] * g)
			challenge_bits >>= 1


#x = commitment to everything
#vote = vote_commitment
#commitments = proofs
def verifyCommitment(x, vote, commitments, rx, G, h, g):
	everything = challengeHash(''.join(map(str,[vote] + list(chain(commitments)))), K) #alphabetize this
	result = commit(Bn.from_hex(everything), Bn.from_decimal(rx), h, g)
	assert(result == x)

def strToEcPt(s, group):
	return EcPt.from_binary(binascii.unhexlify(s), group)

def verifyVotes(ver_d):
	G = EcGroup(int(ver_d['G'])) 
	g = strToEcPt(ver_d['g'], G)
	h = strToEcPt(ver_d['h'], G)
	#print(ver_d['receipts'][0]['voter_id'])
	#verify commitments for each vote
	for receipt in ver_d['receipts']:
		sortc = sorted(receipt['challenges'])
		proof_list = []
		for sk in sortc:
			ktr = []
			for cmt in receipt['challenges'][sk]['proof']:
				ktr.append(strToEcPt(cmt, G))
			proof_list.append(ktr)
		#print(proof_list)
		verifyCommitment(strToEcPt(receipt['commitment_to_everything'], G), receipt['vote_commitment'], proof_list, receipt['rx'], G, h, g)
		verifyChallenge(receipt['challenges'], receipt['vote_commitment'], G, h, g)
	ver_d['receipts'].sort(key = lambda x: x['voter_id'])
	vote_commits = [strToEcPt(v['vote_commitment'], G) for v in ver_d['receipts']]
	#print(vote_commits)
	#verify proofs
	for proof in ver_d['proofs']:
		if proof['proof_type'] == 'unmask':
			verifyPermutation(list(map(lambda s: strToEcPt(s,G) , proof['pm_vote_commitments'].split(' '))), vote_commits, list(map(Bn.from_hex,proof['maskers'].split(' '))), list(map(int, proof['pi'].split(' '))), g)
			#print("ok")
		elif proof['proof_type'] == 'open':
			verifyMaskedCommitments(list(map(lambda s: strToEcPt(s,G), proof['pm_vote_commitments'].split(' '))), proof['comm_pairs'], ver_d['tally'], h, g)
		else:
			print("Unrecognized proof type: " + proof('type'))




ver_dict = None
with open('./verification.json') as data_file:    
    ver_dict = json.load(data_file)

verifyVotes(ver_dict)

print(ver_dict['tally'])

#for candidate in ver_dict['tally']:
#	print("%s: %d" % (rev_d[candidate], tally[candidate]))






