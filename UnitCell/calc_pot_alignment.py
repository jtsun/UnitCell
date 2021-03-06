#!/usr/bin/env python

"""
calc_pot_alignment.py Jeff Doak jeff.w.doak@gmail.com
Calculates the electrostatic alignment between defected and perfect-crystal
supercells. (This script is newer/better than calc_pot_alignment.py).

Possible command line options:
 calc_pot_alignment.py <path to defect dir> <path to host dir> <atom #>
 calc_pot_alignment.py <def dir> <host dir> <atom #> <list of atom type names>
 calc_pot_alignment.py <def dir> <host dir> <dummy #> <name list> <defect atom position>
 calc_pot_alignment.py <def dir> <host dir> <dummy #> <name list>
                        <defect atom position> <corresponding host position>
 calc_pot_alignment.py <def dir> <host dir> <dummy #> <name list>
                        <defect atom position> <corresponding host position> quiet
 calc_pot_alignment.py <def dir> <host dir> <dummy #> <name list>
                        <defect atom position> <corresponding host position> switch quiet

Here, <path to defect dir> and <path to host dir> are the relative paths from
the current directory to the directories containing the defect and host
crystal calculations, respectively; <atom #> is the index of the defect atom's
position in the list of atoms in the defect crystal POSCAR; <list of atom type
names> is a space-separated list of the element symbols (or any string) with
one element for each atom type in the defect crystal POSCAR; <dummy #> is any
integer (this parameter is not used when defect atom positions are given
explicitly); <defect atom position> is a space-separated list of the x, y,
and z coordinates of the defect atom's (or vacancy's) position in the defect
crystal, given in direct coordinates; and <corresponding host position> is a
space-separated list of x, y, and z coordinates (in direct coordinates of the
host crystal) for the position in the host POSCAR which corresponds to the
position of the defect in the defect crystal.

The fourth command is useful when the atom positions in the defect
crystal have been shifted relative to the host crystal to place the defect at
the origin of the defect POSCAR.

The fifth command suppresses all output except for the electrostatic potential
alignment. This is useful for automated calculations.

The sixth command is rarely useful. It moves the defect atom from the bottom
of the list of atoms in the defect poscar or vice versa.
in the same order.

"""

import re
import sys

import numpy as np

from unitcell import UnitCell

def get_el_pots(outcar_name, n_atoms):
    """
    Read in atom-averaged electrostatic potentials from an OUTCAR file.

    Parameters
    ----------
    outcar_name : str
        Path to OUTCAR file.
    n_atoms : int
        Number of atoms in the calculation corresponding to the OUTCAR file.

    Returns
    -------
    charged_pots : numpy array
        Array of electrostatic potentials averaged around each atom (units of
        eV).
        np.shape(charged_pots) == (n_atoms,)

    """
    with open(outcar_name, 'r') as outcar:
        lines = outcar.readlines()
    charged_pots = np.zeros(n_atoms)
    for i in range(len(lines)):
        if lines[i].startswith("  (the norm of the test charge is"):
            j = 1
            k = 0
            while k < n_atoms:
                line = lines[i+j].split()
                while len(line) > 0:
                    temp = line.pop(0)
                    try:
                        k = int(temp)
                    except ValueError:
                        el_str = str(k+1)+r"([-][0-9][0-9]*[.][0-9][0-9]*)"
                        el_reg = re.compile(el_str)
                        k += 1
                        charged_pots[k-1] = float(el_reg.match(temp).group(1))
                    else:
                        charged_pots[k-1] = float(line.pop(0))
                j += 1
            break
    return charged_pots

# Set up input file names
chargedpos = str(sys.argv[1])+"POSCAR"
neutralpos = str(sys.argv[2])+"POSCAR"
chargedout = str(sys.argv[1])+"OUTCAR"
neutralout = str(sys.argv[2])+"OUTCAR"
# number of defect atom in poscar is given as optional 3rd argument, if
# the defect has a position different from 0, 0, 0

# Read in POSCAR of charged calculation
poscar = UnitCell(chargedpos)
if len(sys.argv) > 3:
    center = poscar.atom_positions[int(sys.argv[3])-1]
else:
    center = np.array([0.0, 0.0, 0.0])
neut_center = np.array(center)
if len(sys.argv) > 3+poscar.num_atom_types:
    names = [str(i) for i in sys.argv[4:4+poscar.num_atom_types]]
    poscar.set_atom_names(names)
if len(sys.argv) > 4+poscar.num_atom_types:
    center = [float(i) for i in
              sys.argv[4+poscar.num_atom_types:7+poscar.num_atom_types]]
    neut_center = np.array(center)
if len(sys.argv) > 7+poscar.num_atom_types:
    neut_center = [float(i) for i in
                   sys.argv[7+poscar.num_atom_types:10+poscar.num_atom_types]]
poscar.convention = "D"
poscar.shift(0.5-center[0], 0.5-center[1], 0.5-center[2], "D")
poscar.in_cell()
poscar.scale = 1.0
poscar.convention = "C"

# Move defect atom to top of list if it isn't first and the switch flag is
# used
if str(sys.argv[-2]) == "switch":
    if int(sys.argv[3]) == 1:
        temp_pos = np.delete(poscar.atom_positions, int(sys.argv[3])-1, 0)
        temp_pos = np.insert(temp_pos,
                             len(poscar.atom_positions)-1,
                             poscar.atom_positions[int(sys.argv[3])-1],
                             0,
                            )
        poscar.atom_positions = temp_pos
    elif int(sys.argv[3]) == len(poscar.atom_positions):
        temp_pos = np.delete(poscar.atom_positions, int(sys.argv[3])-1, 0)
        temp_pos = np.insert(temp_pos, 0, poscar.atom_positions[int(sys.argv[3])-1], 0)
        poscar.atom_positions = temp_pos

# Read in POSCAR of neutral calculation
perfect = UnitCell(neutralpos)
perfect.convention = "D"
perfect.shift(0.5-neut_center[0], 0.5-neut_center[1], 0.5-neut_center[2], "D")
perfect.in_cell()
perfect.scale = 1.0
perfect.convention = "C"

# Adjust center to center of cell in cartesian coordinates
center = np.dot(poscar.cell_vec.transpose(), np.array([0.5, 0.5, 0.5]))
neut_center = np.dot(perfect.cell_vec.transpose(), np.array([0.5, 0.5, 0.5]))

# Read in OUTCAR of charged calculation
charged_pots = get_el_pots(chargedout, poscar.num_atoms)
# Reorder electrostatic potentials if defect atom isn't the first, and the
# switch flag is used
if str(sys.argv[-2]) == "switch":
    if int(sys.argv[3]) == 1:
        temp_pots = np.delete(charged_pots, int(sys.argv[3])-1)
        temp_pots = np.insert(temp_pots, len(charged_pots)-1, charged_pots[int(sys.argv[3])-1])
        charged_pots = temp_pots
    elif int(sys.argv[3]) == len(poscar.atom_positions):
        temp_pots = np.delete(charged_pots, int(sys.argv[3])-1)
        temp_pots = np.insert(temp_pots, 0, charged_pots[int(sys.argv[3])-1])
        charged_pots = temp_pots

# Read in OUTCAR of neutral calculation
neutral_pots = get_el_pots(neutralout, perfect.num_atoms)

def list_fit(index, list1, list2):
    """
    Evaluate the fitness function for 2 lists off by 1 element. Assume
    len(list2) > len(list1).

    """
    list2 = np.delete(list2, index, 0)
    return np.linalg.norm(list2-list1)

def list_fit_2(i1, i2, list1, list2):
    list2 = np.delete(list2, [i1, i2], 0)
    return np.linalg.norm(list2-list1)

# Find missing atom in defect/host cell
insert_index = []
if len(poscar.atom_positions)+1 == len(perfect.atom_positions):
    # There is a vacancy defect
    for i in range(len(neutral_pots)):
        insert_index.append(list_fit(i, charged_pots, neutral_pots))
    neutral_pots = np.delete(neutral_pots, np.argsort(insert_index)[0])
    perfect.atom_positions = np.delete(perfect.atom_positions, np.argsort(insert_index)[0], 0)
elif len(poscar.atom_positions) == len(perfect.atom_positions)+1:
    # There is an interstitial defect
    for i in range(len(charged_pots)):
        insert_index.append(list_fit(i, neutral_pots, charged_pots))
    charged_pots = np.delete(charged_pots, np.argsort(insert_index)[0])
    poscar.atom_positions = np.delete(poscar.atom_positions, np.argsort(insert_index)[0], 0)
elif len(poscar.atom_positions)+2 == len(perfect.atom_positions):
    # There is a multi-vacancy defect
    for i in range(len(neutral_pots)-1):
        insert_index.append([])
        for j in range(i+1, len(neutral_pots)):
            insert_index[i].append(list_fit_2(i, j, charged_pots, neutral_pots))
    min_index = np.argmin(np.array(insert_index).flatten())
    min_indices = np.unravel_index(min_index, (len(insert_index), len(insert_index[0])))
    #print min_indices[0]
    #print min_index, min_indices, insert_index[min_indices[0]][min_indices[1]]
    #print perfect.atom_positions[min_indices[0]]-perfect.atom_positions[min_indices[1]]
    neutral_pots = np.delete(neutral_pots, min_indices)
    perfect.atom_positions = np.delete(perfect.atom_positions, min_indices, 0)

delta_pots = charged_pots - neutral_pots

# Average electrostatic potential difference outside 1/2 def-def distance
r_min = np.linalg.norm(poscar.cell_vec[0])/2. #huge assumption that the cell is cubic
radii = [np.linalg.norm(i-center) for i in poscar.atom_positions]
sphere_pots = []
for i in range(len(radii)):
    if radii[i] >= r_min:
        sphere_pots.append(delta_pots[i])

# Print average electrostatic potential difference between defect and host cells
# as a function of distance away from the defect
if str(sys.argv[-1]) != "quiet":
    sorted_radii = np.sort(radii)
    sorted_pots = [delta_pots[i] for i in np.argsort(radii)]
    sorted_names = [poscar.atom_names[i] for i in np.argsort(radii)]
    for i in range(len(sorted_radii)):
        print sorted_radii[i], sorted_pots[i], sorted_names[i]

# Print cell-averaged electrostatic potential difference
if str(sys.argv[-1]) != "quiet":
    print ""
    print "Average over atoms outside radius", r_min, "A centered around defect"
    print "$\Delta V_{el} (eV)$ &", "# atoms in average &", "Std. Dev. (eV)"
    print np.mean(sphere_pots), len(sphere_pots), np.std(sphere_pots)
else:
    print np.mean(sphere_pots)

exit()
