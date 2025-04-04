import os
import collections
import re

import numpy as np
import scipy.io as sio
import torch
from tqdm import tqdm
from celluloid import Camera
import matplotlib.pyplot as plt
import pandas as pd

# from human_body_prior.body_model.body_model import BodyModel
# from human_body_prior.tools.omni_tools import copy2cpu as c2c



# Converting MoVi style mat file to nested dictionary
def mat2dict(filename):
    """Converts MoVi mat files to a python nested dictionary.
    This makes a cleaner representation compared to sio.loadmat
    Arguments:
        filename {str} -- The path pointing to the .mat file which contains
        MoVi style mat structs
    Returns:
        dict -- A nested dictionary similar to the MoVi style MATLAB struct
    """
    # Reading MATLAB file
    data = sio.loadmat(filename, struct_as_record=False, squeeze_me=True)

    # Converting mat-objects to a dictionary
    for key in data:
        if key != "__header__" and key != "__global__" and key != "__version__":
            if isinstance(data[key], sio.matlab.mio5_params.mat_struct):
                data_out = matobj2dict(data[key])
    return data_out


def matobj2dict(matobj):
    """A recursive function which converts nested mat object
    to a nested python dictionaries
    Arguments:
        matobj {sio.matlab.mio5_params.mat_struct} -- nested mat object
    Returns:
        dict -- a nested dictionary
    """
    ndict = {}
    for fieldname in matobj._fieldnames:
        attr = matobj.__dict__[fieldname]
        if isinstance(attr, sio.matlab.mio5_params.mat_struct):
            ndict[fieldname] = matobj2dict(attr)
        elif isinstance(attr, np.ndarray) and fieldname == "move":
            for ind, val in np.ndenumerate(attr):
                ndict[
                    fieldname
                    + str(ind).replace(",", "").replace(")", "").replace("(", "_")
                    ] = matobj2dict(val)
        elif fieldname == "skel":
            tree = []
            for ind in range(len(attr)):
                tree.append(matobj2dict(attr[ind]))
            ndict[fieldname] = tree
        else:
            ndict[fieldname] = attr
    return ndict

### plot & save animation of one sample trajectory for each activity

def animate(data,data_labels, activities, path, joints, normalized = True):    # activities = movement_name_list          
                                                    # data_labels = data_dict["labels_name"]
                                                    # data ==> all trajectories (1319,28,633)  
                                                    # folder path to save animations 

    pick_traj = 5      # Select a trajectory to simulate
    fig, ax = plt.subplots(figsize=(3,4))
    
    if normalized:
        ax.set(xlim=(-5, 5), ylim=(5, -5))
    else:
        ax.set(xlim=(-700, 700), ylim=(700, -700))
    
    ax.get_xaxis().set_label_coords(0.5, 0.12)
    for motion in activities:
       
        camera = Camera(fig)
        print(motion)
        ind = np.where(data_labels== motion)
        seq = data[ind[0][0]]
        df = pd.DataFrame(seq).transpose()
        
        df.columns = joints
        t_range = df.shape[0]
        
        for t in range(t_range):

            # Projectile's trajectory
            x = {}
            y = {}
            for j in range(int(len(joints)/2)):
                    x[joints[j]] = df[joints[j]].to_numpy()
                    y[joints[j+14]] = df[joints[j+14]].to_numpy()
                    # Show Projectile's location
                    ax.plot(x[joints[j]][t], y[joints[j+14]][t], marker='o', markersize=1, markeredgecolor='r', markerfacecolor='r')
                    
            # Show Projectile's trajectory
            ax.plot([x["shoulder1_x"][t],x["chin_x"][t], x["shoulder2_x"][t]],[y["shoulder1_y"][t], y["chin_y"][t],y["shoulder2_y"][t]],'ro-')
            ax.plot([x["shoulder1_x"][t],x["elbow1_x"][t], x["wrist1_x"][t]],[y["shoulder1_y"][t], y["elbow1_y"][t],y["wrist1_y"][t]],'ro-')
            ax.plot([x["shoulder2_x"][t],x["elbow2_x"][t], x["wrist2_x"][t]],[y["shoulder2_y"][t], y["elbow2_y"][t],y["wrist2_y"][t]],'ro-')
            ax.plot([x["shoulder1_x"][t],x["hip1_x"][t], x["hip2_x"][t], x["shoulder2_x"][t]],[y["shoulder1_y"][t], y["hip1_y"][t],y["hip2_y"][t],
            y["shoulder2_y"][t]],'ro-')
            ax.plot([x["hip1_x"][t],x["knee1_x"][t], x["ankle1_x"][t]],[y["hip1_y"][t],y["knee1_y"][t], y["ankle1_y"][t]],'ro-')
            ax.plot([x["hip2_x"][t],x["knee2_x"][t], x["ankle2_x"][t]],[y["hip2_y"][t],y["knee2_y"][t], y["ankle2_y"][t]],'ro-')
            ax.plot([x["forehead_x"][t],x["chin_x"][t]],[y["forehead_y"][t],y["chin_y"][t]],'ro-') 

            # Capture frame
            camera.snap()
        anim = camera.animate(interval = 60, repeat = False)
        anim.save(path+'/{}.mp4'.format(motion))
        
     
def pretty_dict(ndict, indent=0, print_type=False):
    """Visualizes the tree-like structure of a dictionary
    Arguments:
        ndict {dict} -- [the python dictionary to be visualized]
    Keyword Arguments:
        indent {int} -- [number of tab spaces for the indentation]
        (default: {0})
        print_type {bool} -- [True if variable types are printed]
        (default: {False})
    """
    if isinstance(ndict, dict):
        for key, value in ndict.items():
            if print_type:
                print(
                    "\t" * indent + "Key: " + str(key) + ",\t" + "Type: ", type(value),
                )
                pretty_dict(value, indent + 1, True)
            else:
                print("\t" * indent + "Key: " + str(key))
                pretty_dict(value, indent + 1)


# Converting dictionary to namedTuple
def dict2ntuple(ndict):
    """Converts nested (or simple) dictionary to namedTuples
    so that the attributes are accessible by dotted notation.
    Example: subj = mat2dicts(matefilename)
    subj = subj('Subject_15')
    n_subj = dict2ntuple(subj)
    IMU = n_subj.IMU
    Arguments:
        ndict {dict}: python dictionary to be converted to a
        namecTuple. Make sure all keys are made by letters or
        underscore (key names must not by prefixed with underscore)
    Returns:
        namedTuple -- a nested namedTuple object
    """

    if isinstance(ndict, collections.Mapping) and not isinstance(ndict, ProtectedDict):
        for key, value in ndict.items():
            ndict[key] = dict2ntuple(value)
        return dict2tuple(ndict)
    return ndict


def dict2tuple(mapping, name="Dict2ntuple"):
    current_tuple = collections.namedtuple(name, mapping.keys())
    return current_tuple(**mapping)


class ProtectedDict:
    """ ndict2tuple eats all dicts you give it, recursively;
    but what if you actually want a dictionary in there?
    This will stop it. Just do ProtectedDict({...}) or
    ProtectedDict(kwarg=foo).
    """


def amass_fk(npz_data_path, bm_path):
    if torch.cuda.is_available():
        comp_device = torch.device("cuda")
    else:
        comp_device = torch.device("cpu")
    bm = BodyModel(bm_path=bm_path, batch_size=1, num_betas=10).to(
        comp_device
    )
    bdata = np.load(npz_data_path)
    root_orient = torch.Tensor(bdata["poses"][:, :3]).to(comp_device)
    pose_body = torch.Tensor(bdata["poses"][:, 3:66]).to(comp_device)
    pose_hand = torch.Tensor(bdata["poses"][:, 66:]).to(comp_device)
    betas = torch.Tensor(bdata["betas"][:10][np.newaxis]).to(comp_device)
    rootTranslation = bdata["trans"]
    s1, s2 = rootTranslation.shape
    trans = np.expand_dims(rootTranslation, 1)
    joints = np.zeros((bdata["poses"].shape[0], 52, 3))
    verts = np.zeros((bdata["poses"].shape[0], 6890, 3))
    count = 0
    num_frames = bdata["poses"].shape[0]
    for fId in tqdm(range(1, num_frames)):
        body = bm(
            pose_body=pose_body[fId : fId + 1],
            pose_hand=pose_hand[fId : fId + 1],
            betas=betas,
            root_orient=root_orient[fId : fId + 1],
        )
        joints[count] = c2c(body.Jtr[0]) + trans[count]
        verts[count] = c2c(body.v[0]) + trans[count]
        count += 1
    return joints, verts


def npz2movi(npz_bdata_path, bm_path, savefile=False):
    jointsLocation, verts = amass_fk(npz_bdata_path, bm_path)
    file_name = os.path.splitext(os.path.split(npz_bdata_path)[1])[0]
    dir_name = os.path.dirname(npz_bdata_path)
    bdata = np.load(npz_bdata_path)
    verts = 1000 * verts
    jointsLocation = 1000 * jointsLocation
    jointsLocation = jointsLocation[:, :, [1, 0, 2]]
    verts = verts[:, :, [1, 0, 2]]
    jointsLocation[:, :, 0] = -jointsLocation[:, :, 0]
    verts[:, :, 0] = -verts[:, :, 0]
    jointsExpMaps = bdata["poses"]
    jointsBetas = bdata["betas"]
    rootTranslation = bdata["trans"]
    jointsParent = np.array(
        [
            0,
            1,
            1,
            1,
            2,
            3,
            4,
            5,
            6,
            7,
            8,
            9,
            10,
            10,
            10,
            13,
            14,
            15,
            17,
            18,
            19,
            20,
            21,
            23,
            24,
            21,
            26,
            27,
            21,
            29,
            30,
            21,
            32,
            33,
            21,
            35,
            36,
            22,
            38,
            39,
            22,
            41,
            42,
            22,
            44,
            45,
            22,
            47,
            48,
            22,
            50,
            51,
        ]
    )
    file_name = re.sub("poses", "amass", file_name)
    output = {
        "rootTranslation": rootTranslation,
        "jointsLocation": jointsLocation,
        "jointsExpMaps": jointsExpMaps,
        "jointsBetas": jointsBetas,
        "jointsParent": jointsParent,
        "verts": verts,
    }

    if savefile:
        MATLAB_file = dir_name + "/" + file_name + ".mat"
        sio.savemat(
            MATLAB_file,
            {
                "rootTranslation": rootTranslation,
                "jointsLocation": jointsLocation,
                "jointsExpMaps": jointsExpMaps,
                "jointsBetas": jointsBetas,
                "jointsParent": jointsParent,
                "verts": verts,
            },
        )
    return output