import numpy as np
from stl import mesh
import time
import argparse

def main():

    args = parseArgs()

    startTime = time.time()
    transformed_STL = transformation_STL_file(path=args.src.name, cone_type=args.coneType, cone_angle_deg=args.angle, nb_iterations=args.iterations)
    transformed_STL.save(args.dst.name)
    deltaTime = time.time() - startTime
    print(f'Transformation time: {deltaTime}')

def parseArgs():
    parser = argparse.ArgumentParser(description='Transform STL 3D models for conical slicing.')

    DEF_ANGLE = 16.0
    DEF_CONE_TYPE = 'outward'
    DEF_ITEREATIONS = 2
    
    parser.add_argument('-s', '--src', dest='src', help='Input file path', required=True, type=argparse.FileType('r'))
    parser.add_argument('-d', '--dst', dest='dst', help='Output file path', required=True, type=argparse.FileType('w'))
    parser.add_argument('-a', '--angle', dest='angle', help=f'Transformation angle. Defaut {DEF_ANGLE}.', default=DEF_ANGLE, type=float)
    parser.add_argument('-t', '--type', dest='coneType', help=f'Type of the cone. Default {DEF_CONE_TYPE}.', default=DEF_CONE_TYPE, type=str, choices=['outward', 'inward'])
    parser.add_argument('-i', '--iterations', dest='iterations', help=f'Refinement iterations of the STL. 2-3 for regular STLs. Use 0 or 1 if uniformally fine. Large numbers cause huge models and long runtimes. Default {DEF_ITEREATIONS}.', type=int, default=DEF_ITEREATIONS)
    
    args = parser.parse_args()

    return args

def transformation_kegel(points, cone_angle_rad: float, cone_type: str):
    """
    Computes the cone-transformation (x', y', z') = (x / cos(angle), y / cos(angle), z + \sqrt{x^{2} + y^{2}} * tan(angle))
    for a list of points
    :param points: array
        array of points of shape ( , 3)
    :param cone_angle_rad: float
        TODO: description missing
    :param cone_type: string
        String, either 'outward' or 'inward', defines which transformation should be used
    :return: array
        array of transformed points, of same shape as input array
    """
    if cone_type == 'outward':
        c = 1
    elif cone_type == 'inward':
        c = -1
    else:
        raise ValueError('{} is not a admissible type for the transformation'.format(cone_type))
    f = (lambda x, y, z: np.array([x/np.cos(cone_angle_rad), y/np.cos(cone_angle_rad), z + c * np.sqrt(x**2 + y**2)*np.tan(cone_angle_rad)]))
    points_transformed = list(map(f, points[:, 0], points[:, 1], points[:, 2]))
    return np.array(points_transformed)


def refinement_four_triangles(triangle):
    """
    Compute a refinement of a triangle. On every side, the midpoint is added. The three corner points and three
    midpoints result in four smaller triangles.
    :param triangle: array
        array of three points of shape (3, 3) (one triangle)
    :return: array
        array of shape (4, 3, 3) of four triangles
    """
    point1 = triangle[0]
    point2 = triangle[1]
    point3 = triangle[2]
    midpoint12 = (point1 + point2) / 2
    midpoint23 = (point2 + point3) / 2
    midpoint31 = (point3 + point1) / 2
    triangle1 = np.array([point1, midpoint12, midpoint31])
    triangle2 = np.array([point2, midpoint23, midpoint12])
    triangle3 = np.array([point3, midpoint31, midpoint23])
    triangle4 = np.array([midpoint12, midpoint23, midpoint31])
    return np.array([triangle1, triangle2, triangle3, triangle4])


def refinement_triangulation(triangle_array, num_iterations: int):
    """
    Compute a refinement of a triangulation using the refinement_four_triangles function.
    The number of iteration defines, how often the triangulation has to be refined; n iterations lead to
    4^n times many triangles.
    :param triangle_array: array
        array of shape (num_triangles, 3, 3) of triangles
    :param num_iterations: int
    :return: array
        array of shape (num_triangles*4^num_iterations, 3, 3) of triangles
    """
    refined_array = triangle_array
    for i in range(0, num_iterations):
        n_triangles = refined_array.shape[0]*4
        refined_array = np.array(list(map(refinement_four_triangles, refined_array)))
        refined_array = np.reshape(refined_array, (n_triangles, 3, 3))
    return refined_array


def transformation_STL_file(path: str, cone_type: str, cone_angle_deg: float, nb_iterations: int):
    """
    Read a stl-file, refine the triangulation and transform it according to the cone-transformation
    :param path: string
        path to the stl file
    :param cone_type: string
        String, either 'outward' or 'inward', defines which transformation should be used
    :param cone_angle_deg: float
        angle to transform the part
    :param nb_iterations: int
        number of iterations, the triangulation should be refined before the transformation
    :return: mesh object
        transformed triangulation as mesh object which can be stored as stl file
    """
    cone_angle_rad = cone_angle_deg / 180 * np.pi
    my_mesh = mesh.Mesh.from_file(path)
    vectors = my_mesh.vectors
    vectors_refined = refinement_triangulation(vectors, nb_iterations)
    vectors_refined = np.reshape(vectors_refined, (-1, 3))
    vectors_transformed = transformation_kegel(vectors_refined, cone_angle_rad, cone_type)
    vectors_transformed = np.reshape(vectors_transformed, (-1, 3, 3))
    my_mesh_transformed = np.zeros(vectors_transformed.shape[0], dtype=mesh.Mesh.dtype)
    my_mesh_transformed['vectors'] = vectors_transformed
    my_mesh_transformed = mesh.Mesh(my_mesh_transformed)
    return my_mesh_transformed

if __name__ == '__main__':
    main()
