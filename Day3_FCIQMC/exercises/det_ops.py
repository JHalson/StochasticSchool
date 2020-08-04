import numpy as np

class HAM:
    def __init__(self, filename = 'FCIDUMP', p_single = 0.05):
        ''' Define a hamiltonian to sample, as well as its quantum numbers.
        In addition, it defines the probability of generating a single excitation, rather than double
        excitation in the random excitation generator (which is a method of this class).
        Finally, it also defines a reference determinant energy.'''

        # All these quantities are defined by the 'read_in_fcidump' method
        self.nelec = None       # Number of electrons
        self.ms = None          # 2 x spin-polarization
        self.n_alpha = None     # Number of alpha electrons
        self.n_beta = None      # Number of beta electrons
        self.nbasis = None      # Number of spatial orbitals
        self.spin_basis = None  # Number of spin orbitals (= 2 x self.nbasis)

        # The one-electron hamiltonian in the spin-orbital basis 
        self.h1 = None
        # The two-electron hamiltonian in the spin-orbital basis
        # Note that eri[i,j,k,l] = < phi_i(r_1) phi_k(r_2) | 1/r12 | phi_j(r_1) phi_l(r_2) >
        # This ordering is called 'chemical ordering', and means that the first two indices of the array
        # define the charge density for electron 1, and the second two for electron two.
        self.h2 = None
        # The (scalar) nuclear-nuclear repulsion energy
        self.nn = None

        self.read_in_fcidump(filename)

        # The probability of generating a single excitation rather than a double excitation
        self.p_single = p_single

        # Define a reference determinant and reference energy.
        # Ideally, this should be the energy of the lowest-energy determinant in the space.
        # In a HF basis, this will generally be the first occupied orbitals. Assume so.
        self.ref_det = list(range(self.n_alpha)) + list(range(self.nbasis, self.nbasis+self.n_beta))
        print('Initial reference determinant defined with occupied orbitals: {}'.format(self.ref_det))
        return

    def read_in_fcidump(self, filename):
        ''' This function looks (and is!) pretty messy. Don't worry about it too much. It sets up the system parameters
        as defined by the hamiltonian in the file. It sets the following system parameters:

        self.nelec          # Number of electrons
        self.ms             # 2 x spin-polarization
        self.n_alpha        # Number of alpha electrons
        self.n_beta         # Number of beta electrons
        self.nbasis         # Number of spatial orbitals
        self.spin_basis     # Number of spin orbitals (= 2 x self.nbasis)

        as well as the integrals defining the hamiltonian terms:
        self.h1[:,:]        # A self.spin_basis x self.spin_basis matrix of one-electron terms
        self.h2[:,:,:,:]    # A rank-4 self.spin_basis array for the two electron terms
        self.nn             # The (scalar) nuclear repulsion energy

        Note that the integrals are defined in the spin-orbital basis, and the self.h2 term is defined as follows:
        eri[i,j,k,l] = < phi_i(r_1) phi_k(r_2) | 1/r12 | phi_j(r_1) phi_l(r_2) >
        This ordering is called 'chemical ordering', and means that the first two indices of the array
        define the charge density for electron 1, and the second two for electron two.'''
        import os
        import re

        print('Reading in system from file: {}'.format(filename))
        assert(os.path.isfile(os.path.join('./', filename)))

        finp = open(filename, 'r')
        dat = re.split('[=,]', finp.readline())
        while not 'FCI' in dat[0].upper():
            dat = re.split('[=,]', finp.readline())
        self.nbasis = int(dat[1])
        print('Number of spatial orbitals in the system: {}'.format(self.nbasis))
        self.nelec = int(dat[3])
        print('Number of electrons in the system: {}'.format(self.nelec))
        self.ms = int(dat[5])
        print('2 x Spin polarization of system: {}'.format(self.ms))
        self.n_alpha = (self.ms + self.nelec) // 2
        self.n_beta = self.nelec - self.n_alpha
        print('Number of (alpha, beta) electrons: {}, {}'.format(self.n_alpha, self.n_beta))

        # Read in symmetry information, but we are not using it
        sym = []
        dat = finp.readline().strip()
        while not 'END' in dat:
            sym.append(dat)
            dat = finp.readline().strip()

        isym = [x.split('=')[1] for x in sym if 'ISYM' in x]
        if len(isym) > 0:
            isym_out = int(isym[0].replace(',','').strip())
        symorb = ','.join([x for x in sym if 'ISYM' not in x]).split('=')[1]
        orbsym = [int(x.strip()) for x in symorb.replace(',', ' ').split()]

        # Read in integrals, but immediately transform them into a spin-orbital basis.
        # We order things with alpha, then beta spins
        self.spin_basis = 2*self.nbasis
        self.h1 = np.zeros((self.spin_basis, self.spin_basis))
        # Ignore permutational symmetry
        self.h2 = np.zeros((self.spin_basis, self.spin_basis, self.spin_basis, self.spin_basis))
        dat = finp.readline().split()
        while dat:
            ii, jj, kk, ll = [int(x) for x in dat[1:5]] # Note these are 1-indexed
            i = ii-1
            j = jj-1
            k = kk-1
            l = ll-1
            if kk != 0:
                # Two electron integral - 8 spatial permutations x 4 spin (=32) allowed permutations!
                # alpha, alpha, alpha, alpha
                self.h2[i, j, k, l] = float(dat[0])
                self.h2[j, i, k, l] = float(dat[0])
                self.h2[i, j, l, k] = float(dat[0])
                self.h2[j, i, l, k] = float(dat[0])
                self.h2[k, l, i, j] = float(dat[0])
                self.h2[l, k, i, j] = float(dat[0])
                self.h2[k, l, j, i] = float(dat[0])
                self.h2[l, k, j, i] = float(dat[0])

                # beta, beta, beta, beta
                self.h2[i+self.nbasis, j+self.nbasis, k+self.nbasis, l+self.nbasis] = float(dat[0])
                self.h2[j+self.nbasis, i+self.nbasis, k+self.nbasis, l+self.nbasis] = float(dat[0])
                self.h2[i+self.nbasis, j+self.nbasis, l+self.nbasis, k+self.nbasis] = float(dat[0])
                self.h2[j+self.nbasis, i+self.nbasis, l+self.nbasis, k+self.nbasis] = float(dat[0])
                self.h2[k+self.nbasis, l+self.nbasis, i+self.nbasis, j+self.nbasis] = float(dat[0])
                self.h2[l+self.nbasis, k+self.nbasis, i+self.nbasis, j+self.nbasis] = float(dat[0])
                self.h2[k+self.nbasis, l+self.nbasis, j+self.nbasis, i+self.nbasis] = float(dat[0])
                self.h2[l+self.nbasis, k+self.nbasis, j+self.nbasis, i+self.nbasis] = float(dat[0])

                # alpha, alpha, beta, beta
                self.h2[i, j, k+self.nbasis, l+self.nbasis] = float(dat[0])
                self.h2[j, i, k+self.nbasis, l+self.nbasis] = float(dat[0])
                self.h2[i, j, l+self.nbasis, k+self.nbasis] = float(dat[0])
                self.h2[j, i, l+self.nbasis, k+self.nbasis] = float(dat[0])
                self.h2[k, l, i+self.nbasis, j+self.nbasis] = float(dat[0])
                self.h2[l, k, i+self.nbasis, j+self.nbasis] = float(dat[0])
                self.h2[k, l, j+self.nbasis, i+self.nbasis] = float(dat[0])
                self.h2[l, k, j+self.nbasis, i+self.nbasis] = float(dat[0])

                # beta, beta, alpha, alpha
                self.h2[i+self.nbasis, j+self.nbasis, k, l] = float(dat[0])
                self.h2[j+self.nbasis, i+self.nbasis, k, l] = float(dat[0])
                self.h2[i+self.nbasis, j+self.nbasis, l, k] = float(dat[0])
                self.h2[j+self.nbasis, i+self.nbasis, l, k] = float(dat[0])
                self.h2[k+self.nbasis, l+self.nbasis, i, j] = float(dat[0])
                self.h2[l+self.nbasis, k+self.nbasis, i, j] = float(dat[0])
                self.h2[k+self.nbasis, l+self.nbasis, j, i] = float(dat[0])
                self.h2[l+self.nbasis, k+self.nbasis, j, i] = float(dat[0])
            elif kk == 0:
                if jj != 0:
                    # One electron term
                    self.h1[i,j] = float(dat[0])
                    self.h1[j,i] = float(dat[0])
                    self.h1[i+self.nbasis, j+self.nbasis] = float(dat[0])
                    self.h1[j+self.nbasis, i+self.nbasis] = float(dat[0])
                else:
                    # Nuclear repulsion term
                    self.nn = float(dat[0])
            dat = finp.readline().split()

        print('System file read in.')
        finp.close()
        return

    def slater_condon(self, det, excited_det, excit_mat, parity):
        ''' Calculate the hamiltonian matrix element between two determinants, det and excited_det.
        In:
            det:            A list of occupied orbitals in the original det (note should be ordered)
            excited_det:    A list of occupied orbitals in the excited det (note should be ordered)
            excit_mat:      A list of two tuples, giving the orbitals excited from and to respectively
                                (i.e. [(3, 6), (0, 12)] means we have excited from orbitals 3 and 6 to orbitals 0 and 12
                                    for a single excitation, the tuples will just be of length 1)
                                Note: For a diagonal matrix element (i.e. det == excited_det), the excit_mat should be 'None'.
            parity:         The parity of the excitation
        Out: 
            The hamiltonian matrix element'''

        if excit_mat is None:
            # diagonal
            hel = self.nn
            for pos, p in enumerate(det):
                hel += self.h1[p,p]
                for q in det[pos+1:None]:
                    hel += self.h2[p,p,q,q] - self.h2[p,q,q,p]

        elif len(excit_mat[0]) == 1:
            # single
            hel = self.h1[excit_mat[0][0],excit_mat[1][0]]
            for q in det:
                hel += self.h2[excit_mat[0][0], excit_mat[1][0], q, q] - \
                 self.h2[excit_mat[0][0], q, q, excit_mat[1][0]]

        elif len(excit_mat[0]) == 2:
            # double
            hel = self.h2[excit_mat[0][0], excit_mat[1][0], excit_mat[0][1], excit_mat[1][1]] - \
                 self.h2[excit_mat[0][0], excit_mat[1][1], excit_mat[0][1], excit_mat[1][0]]

        else:
            # >2 excitation level
            hel = 0

        if parity is not None: hel *= parity

        return hel

    def excit_gen(self, det):
        from scipy.special import comb
        ''' Take in a determinant, and create a single or double excitation or it.
        This does *not* take into account any spin (or spatial) symmetries.
        The determinant is represented as an ordered list of occupied orbital indices.
        Returns:
            o The singly or doubly-excited determinant as an ordered orbital list (self.p_single should determine this probability)
            o The excitation matrix giving the orbital indices which change (see docstring in the function above for definition)
            o The parity of the excitation
            o The normalized probability of the excitation'''

        excited_det = det.copy()
        single = np.random.random() < self.p_single

        ind = np.random.randint(0, len(excited_det))
        orb_from = excited_det[ind]
        orb_to = np.random.randint(0,2 * self.nbasis)
        while orb_to in det:
            orb_to = np.random.randint(0,2 * self.nbasis)
        excited_det[ind] = orb_to
        perm = elec_exchange_ops(excited_det, ind)
        excited_det = sorted(excited_det)

        if single:
            excit_mat = [(orb_from,), (orb_to,)]
            prob = self.p_single/(self.nelec*(2*self.nbasis - self.nelec))
        else:
            # do a double excitation
            ind = np.random.randint(0, len(excited_det))
            orb_from_2 = excited_det[ind]
            orb_to_2 = np.random.randint(0, 2 * self.nbasis)
            while (orb_to_2 in excited_det) or (orb_to_2 == orb_from) or (orb_from_2 == orb_to):
                # ^ make sure we're not just replacing the singly-excited electron
                ind = np.random.randint(0, len(excited_det))
                orb_from_2 = excited_det[ind]
                orb_to_2 = np.random.randint(0, 2 * self.nbasis)
            excited_det[ind] = orb_to_2
            perm += elec_exchange_ops(excited_det, ind)
            excit_mat = [(orb_from,orb_from_2), (orb_to,orb_to_2)]
            prob = (1 - self.p_single) / (comb(2*self.nbasis - self.nelec, 2)*comb(self.nelec, 2))
            excited_det = sorted(excited_det)

        return excited_det, excit_mat, (-1)**perm, prob

def elec_exchange_ops(det, ind):
    ''' Given a determinant defined by a list of occupied orbitals
    which is ordered apart from one element (ind), find the number of
    local (nearest neighbour) electron exchanges required to order the 
    list of occupied orbitals.
    
    We can assume that there are no repeated elements of the list, and that
    the list is ordered apart from one element on entry.
    
    Return: The number of pairwise permutations required.'''

    perm = 0
    det_copy = det.copy()
    if ind == 0:
        step = 1
    elif (ind == -1) or (ind == len(det)-1):
        step = -1
    else:
        step = 1 if det[ind] > det[ind + 1] else -1
    while det_copy != sorted(det_copy):
        tmp = det_copy[ind+step]
        det_copy[ind+step] = det_copy[ind]
        det_copy[ind] = tmp
        ind+=step
        perm += 1
    return perm

def calc_excit_mat_parity(det, excited_det):
    ''' Given two determinants (excitations of each other), calculate and return 
    the excitation matrix (see the definition in the slater-condon function), 
    and parity of the excitation'''

    # find the indices being excited from
    from_inds = []
    from_orbs = []
    for from_ind, from_orb in enumerate(det):
        if from_orb not in excited_det:
            from_inds.append(from_ind)
            from_orbs.append(from_orb)

    to_inds = []
    to_orbs = []
    for to_ind, to_orb in enumerate(excited_det):
        if to_orb not in det:
            to_inds.append(to_ind)
            to_orbs.append(to_orb)

    # found all the indices
    assert len(from_inds) == len(to_inds)
    excit_mat = [tuple(from_orbs), tuple(to_orbs)]

    perm=0
    det_copy = det.copy()
    for from_orb, to_orb in zip(from_orbs, to_orbs):
        ind = det_copy.index(from_orb)
        det_copy[ind] = to_orb
        perm += elec_exchange_ops(det_copy,ind)
        det_copy = sorted(det_copy)

    parity = (-1)**perm

    if not list(excit_mat):
        excit_mat = parity = None

    return excit_mat, parity

if __name__ == '__main__':
    import matplotlib.pyplot as plt

    # This section is for unit tests for each function written, so that the can be tested in isolation by running this file
    # independently to the rest of the code.
    
    # Test for hamiltonian matrix elements
    # Read in System 
    sys_ham = HAM(filename='FCIDUMP.8H')
    print('Running unit tests for Slater-Condon rules...')
    # Define set of excitations to compute the hamiltonian matrix element
    test_ham_els = [(sys_ham.ref_det, sys_ham.ref_det, None, None),
                    ([1, 4, 6, 7, 8, 9, 10, 11], [1, 4, 6, 7, 8, 9, 10, 11], None, None),
                    ([0, 1, 3, 4, 8, 9, 11, 12], [0, 2, 3, 4, 8, 9, 11, 12], [(1,), (2,)], 1),
                    ([0, 2, 3, 7, 9, 10, 11, 13], [0, 2, 3, 4, 7, 9, 10, 11], [(13,), (4,)], 1),
                    ([0, 2, 3, 7, 9, 10, 11, 13], [0, 2, 5, 7, 9, 11, 13, 15], [(10, 3), (5, 15)], -1),
                    ([0, 1, 2, 3, 8, 9, 10, 11], [0, 2, 3, 5, 8, 10, 11, 14], [(9, 1), (14, 5)], 1)]
    # The correct matrix elements
    correct_hels = [-4.000299230765899, -1.7706124224297999, 0.003968296598667837, 0.0,
                    -0.008689269052231, 0.0001549635629506746]
    # Test each one.
    for i, (det_i, det_j, excit_mat, parity) in enumerate(test_ham_els):
        hel = sys_ham.slater_condon(det_i, det_j, excit_mat, parity)
        if np.allclose(hel, correct_hels[i]):
            print('Hamiltonian matrix element correct! H element = {}'.format(hel))
        else:
            print('*Hamiltonian matrix element incorrect!*')
            print('Initial determinant: {}'.format(str(det_i)))
            print('Excited determinant: {}'.format(str(det_j)))
            print('Orbital excitation matrix: {}'.format(str(excit_mat)))
            print('Parity of excitation: {}'.format(parity))
            print('Expected hamiltonian matrix element: {}'.format(correct_hels[i]))
            print('Returned hamiltonian matrix element: {}'.format(hel))

    # elec_exchange_ops unit tests 
    print('Running unit tests for elec_exchange_ops function...')
    # A list of test determinants and exchanged orbital indices.
    test_dets = [([0,1,2,3,4,5], 0), 
                 ([0,1,2,3,4,5], 3),
                 ([0,1,2,3,4,5], 5),
                 ([3,6,14,8,11], 2),
                 ([14,3,6,8,11], 0),
                 ([0,8,3,6,11],  1),
                 ([1,3,12,0],    3),
                 ([1,3,0,12],    2),
                 ([1,3,2,4],     2),
                 ([1,3,2,4],     1)]
    correct_perms = [0, 0, 0, 2, 4, 2, 3, 2, 1, 1]
    for i, (det, ind) in enumerate(test_dets):
        perm = elec_exchange_ops(det, ind)
        if perm == correct_perms[i]:
            print('Permutation correct! Perm = {}'.format(perm))
        else:
            print('*Permutation incorrect*!')
            print('True permutation number for determinant {} is {}'.format(str(det),correct_perms[i]))
            print('Your function returns instead: {}'.format(perm))

    # excit_gen unit tests
    # Use random initial determinant value 
    det_root = [0, 1, 4, 6, 8, 12, 13, 15]
    print('Running unit tests for excitation generation function, from determinant {}...'.format(str(det_root)))
    sys_ham = HAM(filename='FCIDUMP.8H',p_single=0.1)
    n_att = 10000000
    excited_dets = {}
    for attempt in range(n_att):
        if attempt % 1000 == 0:
            print('Generated {} excitations...'.format(attempt))
        # Generate a random excitation from this root determinant
        excited_det, excit_mat, parity, prob = sys_ham.excit_gen(det_root)

        # Check that the returned determinant is the same length as the original determinant
        assert(len(det_root) == len(excited_det))

        # Check that returned determinant is an ordered list
        assert(all(excited_det[i] <= excited_det[i+1] for i in range(len(excited_det)-1)))

        # Store the excited determinant
        if repr(excited_det) in excited_dets:
            excited_dets[repr(excited_det)] += 1./(prob*n_att)
        else:
            excited_dets[repr(excited_det)] = 1./(prob*n_att)
    # Create list of n_gen / (N_att x prob) for all excited determinants
    print('Total number of excitations generated: {}'.format(len(excited_dets)))
    probs = []
    for excited_det, prob_sum in list(excited_dets.items()):
        print('Excitation generated: {}'.format(excited_det))
        probs.append(prob_sum)
    plt.plot(range(len(probs)), probs, label='normalized generation frequency')
    plt.axhline(1.0,label='Exact distribution desired')
    plt.legend()
    plt.show()

    # Test example for parity
    det_root = [0, 1, 4, 6, 8, 12, 13, 15]
    print('Running unit tests for calc_excit_mat_parity function, from determinant {}...'.format(str(det_root)))
    sys_ham = HAM(filename='FCIDUMP.8H',p_single=0.1)
    # Generate a number of excitations
    for i in range(25):
        # Generate a random excitation from this root determinant
        excited_det, excit_mat, parity, prob = sys_ham.excit_gen(det_root)

        # Now check that the excit_mat and parity are the same if calculated
        # independently from the calc_excit_mat_parity function.
        excit_mat_2, parity_2 = calc_excit_mat_parity(det_root, excited_det)
        if excit_mat_2 == excit_mat and parity == parity_2:
            print('Excitation matrix and parity agree between the two functions for attempt {}'.format(i))
        # Note that the parity should change if we swap the indices of either the excited from or excited to orbitals
        elif parity == -parity_2 and [tuple(reversed(excit_mat[0])), excit_mat[1]] == excit_mat_2:
            print('Excitation matrix and parity agree between the two functions for attempt {} (though the "from" indices are swapped)'.format(i))
        elif parity == -parity_2 and [excit_mat[0], tuple(reversed(excit_mat[1]))] == excit_mat_2:
            print('Excitation matrix and parity agree between the two functions for attempt {} (though the "to" indices are swapped)'.format(i))
        elif parity == parity_2 and [tuple(reversed(excit_mat[0])), tuple(reversed(excit_mat[1]))] == excit_mat_2:
            print('Excitation matrix and parity agree between the two functions for attempt {} (though both sets of indices are swapped)'.format(i))
        else:
            print('Error in getting agreement for the excitation matrix and parity...')
            print('Root determinant: {}'.format(str(det_root)))
            print('Excited determinant: {}'.format(str(excited_det)))
            print('excit_gen parity = {}. calc_excit_mat_parity parity = {}'.format(parity, parity_2))
            print('excit_gen excitation matrix = {}. calc_excit_mat_parity excitation matrix = {}'.format(excit_mat, excit_mat_2))
