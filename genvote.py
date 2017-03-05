from petlib.ec import EcGroup, EcPt
from petlib.bn import Bn
from hashlib import sha512
from genzkp import ZKProof, ZKEnv, ConstGen, Sec
from itertools import chain
from collections import defaultdict, Counter
import binascii
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

def genFakeCommitments(dummy_challenges, k, real_vote):
	randoms = {}
	commitments = defaultdict(list)
	for vote, challenge_str in dummy_challenges.items():
		challenge = challengeHash(challenge_str, k)
		randoms[vote] = [order.random() for i in range(k)]
		challenge_num = int(challenge, 16)
		for i in range(k):
			if (challenge_num & 1) == 1:
				commitments[vote].append(commit(real_vote, randoms[vote][i]))
			else:
				commitments[vote].append(commit(vote, randoms[vote][i]))
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

def castVote(candidate):
	DC = {}
	R = order.random()
	for non_vote in filter(lambda l: l != candidate, candidates):
		DC[non_vote] = ' '.join([getRandomWord() for i in range(4)])
	rc, masks, rb = genRealCommitments(candidate, K, R)
	commitments, randoms = genFakeCommitments(DC, K, candidate)
	randoms[candidate] = rb
	commitments[candidate] = masks
	everything = challengeHash(''.join(map(str,[rc] + list(chain(commitments.values())))), K) #alphabetize this
	rx = order.random()
	x = commit(Bn.from_hex(everything), rx)
	DC[candidate] = ' '.join([getRandomWord() for i in range(4)])  #random challenge real vote
	answers = answerChallenges(DC, randoms, K, R)
	verifyCommitment(x, rc, commitments, rx)
	return (candidate, rc, R, everything, str(x), answers)

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
	return [(votes[pi[i]], r[pi[i]] + maskers[pi[i]]) for i in range(len(votes))]

def verifyMaskedCommitments(pm_vote_commitments, comm_pairs, tally):
	permuted_votes = []
	for comm, unmask in zip(pm_vote_commitments, comm_pairs):
		permuted_votes.append(unmask[0])
		assert(comm == commit(unmask[0], unmask[1]))
	assert(tally == Counter(permuted_votes))

def verifyPermutation(pm_vote_commitments, vote_commits, maskers, pi):
	assert(pm_vote_commitments == [vote_commits[pi[i]] + maskers[pi[i]] * g for i in range(len(votes))])


def EcPtToStr(pt):
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
	for i in range(K):
		if (beacon & 1) == 0:
			verifyPermutation(list(map(lambda s: strToEcPt(s,G) , proofs[i].split(' '))), vote_commits, list(map(Bn.from_hex,masks[i].split(' '))), list(map(int, pis[i].split(' '))))
		else:
			opened = openMaskedCommitments(votes, list(map(Bn.from_hex,masks[i].split(' '))), randoms, list(map(int,pis[i].split(' '))))
			verifyMaskedCommitments(list(map(lambda s: strToEcPt(s,G), proofs[i].split(' '))), opened, tally)
		beacon >>= 1




vote_data = [castVote(random.randint(1,3)) for i in range(10)]
votes = [v[0] for v in vote_data]
vote_commits = [v[1] for v in vote_data]
randoms = [v[2] for v in vote_data]

tally = Counter(votes)

doFiatShamir(votes, vote_commits, randoms, tally)
for candidate in tally:
	print("%s: %d" % (rev_d[candidate], tally[candidate]))







