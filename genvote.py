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


def genRealCommitments(vote, k, R):
	real_commitment = commit(vote, R)
	rb = [order.random() for i in range(k)]
	masks = [commit(vote, R + rb[i]) for i in range(k)]
	return real_commitment, masks, rb

def genFakeCommitments(dummy_challenges, k, real_vote, R):
	randoms = {}
	commitments = defaultdict(list)
	for vote, challenge_str in dummy_challenges.items():
		challenge = challengeHash(challenge_str, k)
		randoms[vote] = [order.random() for i in range(k)]
		challenge_num = int(challenge, 16)
		for i in range(k):
			if (challenge_num & 1) == 1:
				commitments[vote].append(commit(real_vote, R + randoms[vote][i]))
			else:
				commitments[vote].append(commit(vote, R + randoms[vote][i]))
			challenge_num >>= 1
	return commitments, randoms

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

def answerChallenges(challenges, randoms, k, R):
	answers = defaultdict(list)
	for vote, challenge_str in challenges.items():
		challenge = challengeHash(challenge_str, k)
		challenge_num = int(challenge, 16)
		for i in range(k):
			if (challenge_num & 1) == 1:
				answers[vote].append(randoms[vote][i])
			else:
				answers[vote].append(R + randoms[vote][i])
			challenge_num >>= 1
	return answers


K = 128

d = {'ALICE': 1, 'BETTY': 2, 'CHARLIE': 3}
rev_d = {v:k for k,v in d.items()}

candidates = [d['ALICE'], d['BETTY'], d['CHARLIE']]

dictionary_words = None
with open('/usr/share/dict/words') as f:
	dictionary_words = list(map(str.strip,f.readlines()))

def getRandomWord():
	return random.choice(dictionary_words)

def serializeEcPts(d):
	new_d = dict(d)
	for key, value in new_d.items():
		if isinstance(value, EcPt):
			new_d[key] = EcPtToStr(value)
		elif isinstance(value, dict):
			new_d[key] = serializeEcPts(value)
		elif isinstance(value, list):
			new_d[key] = list(map(EcPtToStr, value))
		elif isinstance(value, tuple):
			new_d[key] = tuple(map(EcPtToStr, value))
	return new_d

def castVote(voter_id, candidate):
	DC = {}
	R = order.random()
	for non_vote in filter(lambda l: l != candidate, candidates):
		DC[non_vote] = ' '.join([getRandomWord() for i in range(4)])
	rc, masks, rb = genRealCommitments(candidate, K, R)
	commitments, randoms = genFakeCommitments(DC, K, candidate, R)
	randoms[candidate] = rb
	commitments[candidate] = masks
	everything = challengeHash(''.join(map(str,[rc] + list(chain(commitments.values())))), K) #alphabetize this
	rx = order.random()
	x = commit(Bn.from_hex(everything), rx)
	DC[candidate] = ' '.join([getRandomWord() for i in range(4)])  #random challenge real vote
	answers = answerChallenges(DC, randoms, K, R)
	verifyCommitment(x, rc, commitments, rx)
	challenge_dict = {candidate: {'challenge': DC[candidate], 'answer': list(map(str,answers[candidate])), 'proof': commitments[candidate]} for candidate in DC}
	receipt = serializeEcPts({'voter_id': voter_id, 'challenges': challenge_dict, 'vote_commitment': rc, 'rx': str(rx), 'commitment_to_everything': x})
	return (candidate, rc, R, everything, str(x), answers, receipt)

def verifyChallenge(cd, vote_commitment):
	vc = strToEcPt(vote_commitment, G)
	for candidate in cd:
		answers = list(map(Bn.from_decimal,cd[candidate]['answer']))
		proofs = list(map(lambda l: strToEcPt(l, G), cd[candidate]['proof']))
		challenge_bits = int(challengeHash(cd[candidate]['challenge'], K), 16)
		for i in range(K):
			if (challenge_bits & 1) == 0:
				assert(proofs[i] == commit(candidate, answers[i]))
			else:
				assert(proofs[i] == vc + answers[i] * g)
			challenge_bits >>= 1




def verifyCommitment(x, vote, commitments, rx):
	everything = challengeHash(''.join(map(str,[vote] + list(chain(commitments.values())))), K) #alphabetize this
	result = commit(Bn.from_hex(everything), rx)
	assert(result == x)

def permuteAndMask(votes, vote_commitments):
	pi = list(range(len(votes)))
	random.shuffle(pi)
	maskers = [order.random() for i in range(len(votes))]
	pm_vote_commitments = [vote_commitments[pi[i]] +  maskers[pi[i]] * g for i in range(len(votes))]
	return pm_vote_commitments, maskers, pi

def openMaskedCommitments(votes, maskers, r, pi):
	return [(votes[pi[i]], str(r[pi[i]] + maskers[pi[i]])) for i in range(len(votes))]

def verifyMaskedCommitments(pm_vote_commitments, comm_pairs, tally):
	permuted_votes = []
	for comm, unmask in zip(pm_vote_commitments, comm_pairs):
		permuted_votes.append(unmask[0])
		assert(comm == commit(unmask[0], Bn.from_decimal(unmask[1])))
	assert(tally == Counter(permuted_votes))

def verifyPermutation(pm_vote_commitments, vote_commits, maskers, pi):
	assert(pm_vote_commitments == [vote_commits[pi[i]] + maskers[pi[i]] * g for i in range(len(votes))])


def EcPtToStr(pt):
	if not isinstance(pt, EcPt):
		return pt
	return binascii.hexlify(pt.export()).decode('utf8')

def strToEcPt(s, group):
	return EcPt.from_binary(binascii.unhexlify(s), group)


def doFiatShamir(votes, vote_commits, randoms, tally):
	pmv_masks_pi = [permuteAndMask(votes, vote_commits) for i in range(K)]
	proofs = [' '.join(map(EcPtToStr, p[0])) for p in pmv_masks_pi]
	masks = [' '.join(map(lambda l: l.hex(), p[1])) for p in pmv_masks_pi]
	pis = [' '.join(map(str, p[2])) for p in pmv_masks_pi]
	proof_str = ''.join(proofs)
	beacon = int(challengeHash(proof_str, K), 16)
	proof_l = []
	for i in range(K):
		p_dict = {}
		if (beacon & 1) == 0:
			p_dict['proof_type'] = 'unmask'
			p_dict['maskers'] = masks[i]
			p_dict['pi'] = pis[i]
			p_dict['pm_vote_commitments'] = proofs[i]
			verifyPermutation(list(map(lambda s: strToEcPt(s,G) , proofs[i].split(' '))), vote_commits, list(map(Bn.from_hex,masks[i].split(' '))), list(map(int, pis[i].split(' '))))
		else:
			opened = openMaskedCommitments(votes, list(map(Bn.from_hex,masks[i].split(' '))), randoms, list(map(int,pis[i].split(' '))))
			p_dict['proof_type'] = 'open'
			print(opened)
			p_dict['comm_pairs'] = serializeEcPts(opened)
			p_dict['pm_vote_commitments'] = proofs[i]
			verifyMaskedCommitments(list(map(lambda s: strToEcPt(s,G), proofs[i].split(' '))), opened, tally)
		beacon >>= 1
		proof_l.append(dict(p_dict))
	return proof_l




vote_data = [castVote(str(uuid.uuid4()), random.randint(1,3)) for i in range(10)]
vote_data.sort(key = lambda x: x[6]['voter_id'])
votes = [v[0] for v in vote_data]
vote_commits = [v[1] for v in vote_data]
randoms = [v[2] for v in vote_data]

receipts = [v[6] for v in vote_data]
verifyChallenge(receipts[0]['challenges'], receipts[0]['vote_commitment'])
#print(receipts_json)

tally = Counter(votes)
print(tally)

proofs = doFiatShamir(votes, vote_commits, randoms, tally)
big_dict = {'precinct-id': '0', 'receipts': receipts, 'tally': tally, 'proofs': proofs}
json_str = json.dumps(big_dict)
#print(json.dumps(big_dict))
for candidate in tally:
	print("%s: %d" % (rev_d[candidate], tally[candidate]))
with open("./verification.json", 'w') as f:
	f.write(json_str)






