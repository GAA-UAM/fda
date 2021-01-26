from typing import Optional, Tuple, TypeVar

import numpy as np
import scipy.linalg

from .._typing import DomainRangeLike
from ._basis import Basis

T = TypeVar("T", bound='FiniteElement')


class FiniteElement(Basis):
    """Finite element basis.

    Given a n-dimensional grid made of simplices, each element of the basis
    is a piecewise linear function that takes the value 1 at exactly one
    vertex and 0 in the other vertices.

    Parameters:
        vertices: The vertices of the grid.
        cells: A list of individual cells, consisting in the indexes of
            :math:`n+1` vertices for an n-dimensional domain space.

    Examples:

        >>> basis = FiniteElement(
        ...     vertices=[[0, 0], [0, 1], [1, 0], [1, 1]],
        ...     cells=[[0, 1, 2], [1, 2, 3]],
        ...     domain_range=[(0, 1), (0, 1)],
        ... )

        Evaluates all the functions in the basis in a list of discrete
        values.

        >>> basis([[0.1, 0.1], [0.6, 0.6], [0.1, 0.2], [0.8, 0.9]])
        array([[[ 0.8],
                [ 0. ],
                [ 0.7],
                [ 0. ]],
               [[ 0.1],
                [ 0.4],
                [ 0.2],
                [ 0.2]],
               [[ 0.1],
                [ 0.4],
                [ 0.1],
                [ 0.1]],
               [[ 0. ],
                [ 0.2],
                [ 0. ],
                [ 0.7]]])

    """

    def __init__(
        self,
        vertices: np.ndarray,
        cells: np.ndarray,
        domain_range: Optional[DomainRangeLike] = None,
    )-> None:
        Basis.__init__(self, domain_range=domain_range, n_basis=len(vertices))
        self.vertices = np.asarray(vertices)
        self.cells = np.asarray(cells)

    def _barycentric_coords(self, points: np.ndarray) -> np.ndarray:
        """
        Find the barycentric coordinates of each point in each cell.

        Only works for simplex cells.

        """
        cell_coordinates = self.vertices[self.cells]

        cartesian_matrix = np.append(
            cell_coordinates,
            np.ones(cell_coordinates.shape[:-1] + (1,)),
            axis=-1,
        )

        cartesian_vector = np.append(
            points,
            np.ones(points.shape[:-1] + (1,)),
            axis=-1,
        )

        coords = np.linalg.solve(
            np.swapaxes(cartesian_matrix, -2, -1),
            cartesian_vector.T[np.newaxis, ...],
        )

        return np.swapaxes(coords, -2, -1)

    def _cell_points_values(self, points: np.ndarray) -> np.ndarray:
        """
        Compute the values of each point in each of the vertices of each cell.

        Only works for simplex cells.

        """
        barycentric_coords = self._barycentric_coords(points)

        # Remove values outside each cell
        wrong_vals = np.any(
            (barycentric_coords < 0) | (barycentric_coords > 1),
            axis=-1,
        )

        barycentric_coords[wrong_vals] = 0

        points_in_cells = np.any(barycentric_coords, axis=-1)
        n_cells_per_point = np.sum(points_in_cells, axis=0)

        barycentric_coords /= n_cells_per_point[:, np.newaxis]

        return barycentric_coords

    def _evaluate(self, eval_points: np.ndarray) -> np.ndarray:

        points_values_per_cell = self._cell_points_values(eval_points)

        cell_points_values = np.swapaxes(points_values_per_cell, -2, -1)
        cell_points_values = cell_points_values.reshape(-1, len(eval_points))
        indexes = self.cells.ravel()

        eval_matrix = np.zeros((self.n_basis, len(eval_points)))
        np.add.at(eval_matrix, indexes, cell_points_values)

        return eval_matrix