#!/usr/bin/env python
# -*- coding: utf-8 -*-
from lego_robot import *
from slam_b_library import filter_step
from slam_04_a_project_landmarks import\
     compute_scanner_cylinders, write_cylinders
from math import sqrt, atan2
import numpy as np

'''
For each cylinder in the scan, find its cartesian coordinates, in the world coordinate system.
Find the closest pairs of cylinders from the scanner and cylinders from the reference, and the optimal transformation
which aligns them.
Then, use this transform to correct the pose.
04_d_apply_transform
Claus Brenner, 14 NOV 2012
'''

def distance_btw(p1,p2):
    return ((p1[0]-p2[0])**2 + (p1[1]-p2[1])**2)**0.5

def find_cylinder_pairs(cylinders, reference_cylinders, max_radius):
    '''
    Given a list of cylinders (points) and reference_cylinders:
    For every cylinder, find the closest reference_cylinder and add
    the index pair (i, j), where i is the index of the cylinder, and
    j is the index of the reference_cylinder, to the result list.
    This is the function developed in slam_04_b_find_cylinder_pairs.
    :param cylinders:
    :param reference_cylinders:
    :param max_radius:
    :return: cylinder_pairs
    '''
    cylinder_pairs = []
    for i in range(len(cylinders)):
        temp = []
        for j in range(len(reference_cylinders)):
            dist = distance_btw(cylinders[i], reference_cylinders[j])
            temp.append(dist)
        if min(temp) < max_radius:
            cylinder_pairs.append((i, temp.index(min(temp))))
    return cylinder_pairs



def compute_center(point_list):
    '''
    Given a point list, return the center of mass.
    :param point_list:
    :return: center of mass.Summation(point set)/ length of point set
    '''
    # Safeguard against empty list.
    if not point_list:
        return (0.0, 0.0)
    # If not empty, sum up and divide.
    sx = sum([p[0] for p in point_list])
    sy = sum([p[1] for p in point_list])
    return (sx / len(point_list), sy / len(point_list))


def estimate_transform(left_list, right_list, fix_scale = False):
    '''
    Given a left_list of points and a right_list of points, compute
    the parameters of a similarity transform: scale, rotation, translation.
    If fix_scale is True, use the fixed scale of 1.0.
    The returned value is a tuple of:
    (scale, cos(angle), sin(angle), x_translation, y_translation)
    i.e., the rotation angle is not given in radians, but rather in terms
    of the cosine and sine.
    :param left_list:
    :param right_list:
    :param fix_scale:
    :return: la, c, s, tx, ty
    '''
    if len(left_list) < 2 or len(right_list) <2:
        return None
    # Compute left and right center.
    lc = compute_center(left_list)
    rc = compute_center(right_list)
    # --->>> Insert here your code to compute lambda, c, s and tx, ty.
    m = len(left_list)
    #Compute reduced coordinates.
    li = [tuple(np.subtract(l,lc)) for l in left_list]
    ri = [tuple(np.subtract(r,rc)) for r in right_list]

    cs,ss,rr,ll = 0.0,0.0,0.0,0.0

    for i in range(m):
        cs += (ri[i][0] * li[i][0]) + (ri[i][1] * li[i][1]) #cosine sum
        ss += -(ri[i][0] * li[i][1]) + (ri[i][1] * li[i][0]) # sin sum
        rr +=  (ri[i][0]* ri[i][0]) + (ri[i][1]*ri[i][1])
        ll +=  (li[i][0]* li[i][0]) + (li[i][1]*li[i][1])
    #Compute Scale
    if fix_scale:
        la = 1.0
    else:
        la = sqrt(rr/ll)
    #Compute Rotation
    if cs == 0.0 or ss == 0.0:
        return None
    else:
        c = cs/sqrt(cs**2 + ss **2)
        s = ss / sqrt(cs ** 2 + ss ** 2)
    #Compute Translation
    tx = rc[0] - (la * (c * lc[0]) - (s * lc[1]))
    ty = rc[1] - (la * (s * lc[0]) + (c * lc[1]))
    return la, c, s, tx, ty


def apply_transform(trafo, p):
    '''
    Given a similarity transformation:
    trafo = (scale, cos(angle), sin(angle), x_translation, y_translation)
    and a point p = (x, y), return the transformed point.
    :param trafo:
    :param p:
    :return: x,y
    '''
    la, c, s, tx, ty = trafo
    lac = la * c
    las = la * s
    x = lac * p[0] - las * p[1] + tx
    y = las * p[0] + lac * p[1] + ty
    return (x, y)


def correct_pose(pose, trafo):
    '''
    Correct the pose = (x, y, heading) of the robot using the given
    similarity transform. Note this changes the position as well as
    the heading.
    :param pose:
    :param trafo:
    :return: x,y,theta
    '''
    # --->>> This is what you'll have to implement.
    la, c, s, tx, ty = trafo
    theta  = pose[2] + atan2(s,c)
    x,y = apply_transform(trafo,pose)
    return (x,y,theta)


if __name__ == '__main__':
    # The constants we used for the filter_step.
    scanner_displacement = 30.0
    ticks_to_mm = 0.349
    robot_width = 150.0

    # The constants we used for the cylinder detection in our scan.    
    minimum_valid_distance = 20.0
    depth_jump = 100.0
    cylinder_offset = 90.0

    # The maximum distance allowed for cylinder assignment.
    max_cylinder_distance = 400.0

    # The start pose we obtained miraculously.
    pose = (1850.0, 1897.0, 3.717551306747922)

    # Read the logfile which contains all scans.
    logfile = LegoLogfile()
    logfile.read("robot4_motors.txt")
    logfile.read("robot4_scan.txt")

    # Also read the reference cylinders (this is our map).
    logfile.read("robot_arena_landmarks.txt")
    reference_cylinders = [l[1:3] for l in logfile.landmarks]

    out_file = file("apply_transform.txt", "w")
    for i in xrange(len(logfile.scan_data)):
        # Compute the new pose.
        pose = filter_step(pose, logfile.motor_ticks[i],
                           ticks_to_mm, robot_width,
                           scanner_displacement)

        # Extract cylinders, also convert them to world coordinates.
        cartesian_cylinders = compute_scanner_cylinders(
            logfile.scan_data[i],
            depth_jump, minimum_valid_distance, cylinder_offset)
        world_cylinders = [LegoLogfile.scanner_to_world(pose, c)
                           for c in cartesian_cylinders]

        # For every cylinder, find the closest reference cylinder.
        cylinder_pairs = find_cylinder_pairs(
            world_cylinders, reference_cylinders, max_cylinder_distance)

        # Estimate a transformation using the cylinder pairs.
        trafo = estimate_transform(
            [world_cylinders[pair[0]] for pair in cylinder_pairs],
            [reference_cylinders[pair[1]] for pair in cylinder_pairs],
            fix_scale = True)

        # Transform the cylinders using the estimated transform.
        transformed_world_cylinders = []
        if trafo:
            transformed_world_cylinders =\
                [apply_transform(trafo, c) for c in
                 [world_cylinders[pair[0]] for pair in cylinder_pairs]]

        # Also apply the trafo to correct the position and heading.
        if trafo:
            pose = correct_pose(pose, trafo)

        # Write to file.
        # The pose.
        print >> out_file, "F %f %f %f" % pose
        # The detected cylinders in the scanner's coordinate system.
        write_cylinders(out_file, "D C", cartesian_cylinders)
        # The detected cylinders, transformed using the estimated trafo.
        write_cylinders(out_file, "W C", transformed_world_cylinders)

    out_file.close()
