import numpy as np
import hppfcl as fcl
import pinocchio
from example_robot_data import load
from pinocchio.visualize import MeshcatVisualizer
from pinocchio import GeometryType
from time import sleep

from os.path import join, dirname, abspath

robot = load("anymal")
model = robot.model
data = robot.data

state_name = "standing"

robot.q0 = robot.model.referenceConfigurations[state_name]

pinocchio.forwardKinematics(model, data, robot.q0)

lfFoot, rfFoot, lhFoot, rhFoot = "LF_FOOT", "RF_FOOT", "LH_FOOT", "RH_FOOT"

foot_frames = [lfFoot, rfFoot, lhFoot, rhFoot]
foot_frame_ids = [robot.model.getFrameId(frame_name) for frame_name in foot_frames]
foot_joint_ids = [
    robot.model.frames[robot.model.getFrameId(frame_name)].parent
    for frame_name in foot_frames
]
pinocchio.forwardKinematics(model, data, robot.q0)
pinocchio.framesForwardKinematics(model, data, robot.q0)

constraint_models = []

for j, frame_id in enumerate(foot_frame_ids):
    contact_model_lf1 = pinocchio.RigidConstraintModel(
        pinocchio.ContactType.CONTACT_3D,
        robot.model,
        foot_joint_ids[j],
        robot.model.frames[frame_id].placement,
        0,
        data.oMf[frame_id],
    )

    constraint_models.extend([contact_model_lf1])

robot.initViewer()
robot.loadViewerModel("pinocchio")
gui = robot.viewer.gui
robot.display(robot.q0)
window_id = robot.viewer.gui.getWindowID("python-pinocchio")

robot.viewer.gui.setBackgroundColor1(window_id, [1.0, 1.0, 1.0, 1.0])
robot.viewer.gui.setBackgroundColor2(window_id, [1.0, 1.0, 1.0, 1.0])
robot.viewer.gui.addFloor("hpp-gui/floor")

robot.viewer.gui.setScale("hpp-gui/floor", [0.5, 0.5, 0.5])
robot.viewer.gui.setColor("hpp-gui/floor", [0.7, 0.7, 0.7, 1.0])
robot.viewer.gui.setLightingMode("hpp-gui/floor", "OFF")

robot.display(robot.q0)

constraint_datas = [cm.createData() for cm in constraint_models]

q = robot.q0.copy()

pinocchio.computeAllTerms(model, data, q, np.zeros(model.nv))
kkt_constraint = pinocchio.ContactCholeskyDecomposition(model, constraint_models)
constraint_dim = sum([cm.size() for cm in constraint_models])
N = 100000
eps = 1e-10
mu = 0.0
# q_sol = (q[:] + np.pi) % np.pi - np.pi
q_sol = q.copy()
robot.display(q_sol)

# Bring CoM between the two feet.

mass = data.mass[0]


def squashing(model, data, q_in):
    q = q_in.copy()
    y = np.ones((constraint_dim))

    N_full = 200

    # Decrease CoMz by 0.2
    com_drop_amp = 0.2
    pinocchio.computeAllTerms(model, data, q, np.zeros(model.nv))
    com_base = data.com[0].copy()
    kp = 1.0
    speed = 1.0
    com_des = lambda k: com_base - np.array(
        [0.0, 0.0, np.abs(com_drop_amp * np.sin(2.0 * np.pi * k * speed / (N_full)))]
    )
    for k in range(N):
        pinocchio.computeAllTerms(model, data, q, np.zeros(model.nv))
        pinocchio.computeJointJacobians(model, data, q)
        pinocchio.computeJointJacobians(model, data, q)
        com_act = data.com[0].copy()
        com_err = com_act - com_des(k)
        kkt_constraint.compute(model, data, constraint_models, constraint_datas, mu)
        constraint_value = np.concatenate(
            [cd.c1Mc2.translation for cd in constraint_datas]
        )
        # constraint_value = np.concatenate([pinocchio.log6(cd.c1Mc2) for cd in constraint_datas])
        J = np.vstack(
            [
                pinocchio.getFrameJacobian(
                    model, data, cm.joint1_id, cm.joint1_placement, cm.reference_frame
                )[:3, :]
                for cm in constraint_models
            ]
        )
        primal_feas = np.linalg.norm(constraint_value, np.inf)
        dual_feas = np.linalg.norm(J.T.dot(constraint_value + y), np.inf)
        print("primal_feas:", primal_feas)
        print("dual_feas:", dual_feas)
        # if primal_feas < eps and dual_feas < eps:
        #    print("Convergence achieved")
        #    break
        print("constraint_value:", np.linalg.norm(constraint_value))
        print("com_error:", np.linalg.norm(com_err))
        rhs = np.concatenate(
            [-constraint_value - y * mu, kp * mass * com_err, np.zeros(model.nv - 3)]
        )
        dz = kkt_constraint.solve(rhs)
        dy = dz[:constraint_dim]
        dq = dz[constraint_dim:]
        alpha = 1.0
        q = pinocchio.integrate(model, q, -alpha * dq)
        y -= alpha * (-dy + y)
        robot.display(q)
        sleep(0.05)
    return q


q_new = squashing(model, data, robot.q0)
