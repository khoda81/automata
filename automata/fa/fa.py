#!/usr/bin/env python3
"""Classes and methods for working with all finite automata."""
import abc
import os
import pathlib
import uuid
from collections import defaultdict
from typing import Any, Dict, Generator, Iterable, List, Optional, Set, Tuple, Union

from automata.base.automaton import Automaton, AutomatonStateT

# Optional imports for use with visual functionality
try:
    import coloraide
    import pygraphviz as pgv
except ImportError:
    _visual_imports = False
else:
    _visual_imports = True


FAStateT = AutomatonStateT


class FA(Automaton, metaclass=abc.ABCMeta):
    """An abstract base class for finite automata."""

    __slots__ = tuple()

    @staticmethod
    def get_state_name(state_data: FAStateT) -> str:
        """
        Get an string representation of a state. This is used for displaying and
        uses `str` for any unsupported python data types.
        """
        if isinstance(state_data, str):
            if state_data == "":
                return "λ"

            return state_data

        elif isinstance(state_data, (set, frozenset, tuple)):
            inner = ", ".join(FA.get_state_name(sub_data) for sub_data in state_data)
            if isinstance(state_data, (set, frozenset)):
                if state_data:
                    return "{" + inner + "}"
                else:
                    return "∅"

            elif isinstance(state_data, tuple):
                return "(" + inner + ")"

        return str(state_data)

    @staticmethod
    def get_edge_name(symbol: str) -> str:
        return "ε" if symbol == "" else str(symbol)

    @abc.abstractmethod
    def iter_transitions(self) -> Generator[Tuple[FAStateT, FAStateT, str], None, None]:
        """
        Iterate over all transitions in the automaton. Each transition is a tuple
        of the form (from_state, to_state, symbol)
        """

    def show_diagram(
        self,
        input_str: Optional[str] = None,
        path: Union[str, os.PathLike, None] = None,
        *,
        engine: Optional[str] = None,
        view=False,
        cleanup: bool = True,
        horizontal: bool = True,
        reverse_orientation: bool = False,
        fig_size: Optional[Tuple] = None,
        font_size: float = 14.0,
        arrow_size: float = 0.85,
        state_separation: float = 0.5,
    ) -> pgv.AGraph:
        """
        Generates the graph associated with the given DFA.
        Args:
            input_str (str, optional): String list of input symbols. Defaults to None.
            - path (str or os.PathLike, optional): Path to output file. If
              None, the output will not be saved.
            - view (bool, optional): Storing and displaying the graph as a pdf.
              Defaults to False.
            - cleanup (bool, optional): Garbage collection. Defaults to True.
              horizontal (bool, optional): Direction of node layout. Defaults
              to True.
            - reverse_orientation (bool, optional): Reverse direction of node
              layout. Defaults to False.
            - fig_size (tuple, optional): Figure size. Defaults to None.
            - font_size (float, optional): Font size. Defaults to 14.0.
            - arrow_size (float, optional): Arrow head size. Defaults to 0.85.
            - state_separation (float, optional): Node distance. Defaults to 0
              5.
        Returns:
            Digraph: The graph in dot format.
        """

        if not _visual_imports:
            raise ImportError("Missing visual imports.")

        # Defining the graph.
        graph = pgv.AGraph(strict=False, directed=True)

        # TODO test fig_size
        if fig_size is not None:
            graph.graph_attr.update(size=", ".join(map(str, fig_size)))

        graph.graph_attr.update(ranksep=str(state_separation))
        font_size_str = str(font_size)
        arrow_size_str = str(arrow_size)

        if horizontal:
            graph.graph_attr.update(rankdir="LR")
        if reverse_orientation:
            if horizontal:
                graph.graph_attr.update(rankdir="RL")
            else:
                graph.graph_attr.update(rankdir="BT")

        # we use a random uuid to make sure that the null node has a
        # unique id to avoid colliding with other states.
        null_node = str(uuid.uuid4())
        graph.add_node(
            null_node,
            label="",
            tooltip=".",
            shape="point",
            fontsize=font_size_str,
        )
        initial_node = self.get_state_name(self.initial_state)
        graph.add_edge(
            null_node,
            initial_node,
            tooltip="->" + initial_node,
            arrowsize=arrow_size_str,
        )

        for state in self.states:
            shape = "doublecircle" if state in self.final_states else "circle"
            node = self.get_state_name(state)
            graph.add_node(node, shape=shape, fontsize=font_size_str)

        is_edge_drawn = defaultdict(lambda: False)
        if input_str is not None:
            input_path, is_accepted = self._get_input_path(input_str=input_str)

            start_color = coloraide.Color("#ff0")
            end_color = (
                coloraide.Color("#0f0") if is_accepted else coloraide.Color("#f00")
            )
            interpolation = coloraide.Color.interpolate(
                [start_color, end_color], space="srgb"
            )

            # find all transitions in the finite state machine with traversal.
            for transition_index, (from_state, to_state, symbol) in enumerate(
                input_path, start=1
            ):
                color = interpolation(transition_index / len(input_path))
                label = self.get_edge_name(symbol)

                is_edge_drawn[from_state, to_state, symbol] = True
                graph.add_edge(
                    self.get_state_name(from_state),
                    self.get_state_name(to_state),
                    label=f"<{label} <b>[<i>#{transition_index}</i>]</b>>",
                    arrowsize=arrow_size_str,
                    fontsize=font_size_str,
                    color=color.to_string(hex=True),
                    penwidth="2.5",
                )

        edge_labels = defaultdict(list)
        for from_state, to_state, symbol in self.iter_transitions():
            if is_edge_drawn[from_state, to_state, symbol]:
                continue

            from_node = self.get_state_name(from_state)
            to_node = self.get_state_name(to_state)
            label = self.get_edge_name(symbol)
            edge_labels[from_node, to_node].append(label)

        for (from_node, to_node), labels in edge_labels.items():
            graph.add_edge(
                from_node,
                to_node,
                label=",".join(sorted(labels)),
                arrowsize=arrow_size_str,
                fontsize=font_size_str,
            )

        # Set layout
        if engine is None:
            engine = "dot"

        graph.layout(prog=engine)

        # Write diagram to file. PNG, SVG, etc.
        # TODO gotta fix this
        if path is not None:
            save_path_final: pathlib.Path = pathlib.Path(path)

            # directory = save_path_final.parent
            # directory.mkdir(parents=True, exist_ok=True)
            # filename = save_path_final.stem
            format = (
                save_path_final.suffix.split(".")[1] if save_path_final.suffix else None
            )

            graph.draw(
                path=save_path_final,
                format=format,
                # cleanup=cleanup,
                # view=view,
            )

        return graph

    @abc.abstractmethod
    def _get_input_path(
        self, input_str: str
    ) -> Tuple[List[Tuple[FAStateT, FAStateT, str]], bool]:
        """Calculate the path taken by input."""

        raise NotImplementedError(
            f"_get_input_path is not implemented for {self.__class__}"
        )

    def _repr_mimebundle_(
        self,
        include: Optional[Iterable[str]] = None,
        exclude: Optional[Iterable[str]] = None,
        **_,
    ) -> Dict[str, Union[bytes, str]]:
        DEFAULT_FORMATS = {"image/svg+xml"}
        # TODO add proper support for include/exclude
        # DEFAULT_FORMATS = frozenset(("jpeg", "jpg", "png", "svg"))

        diagram_graph = self.show_diagram()

        include = set(include) if include is not None else DEFAULT_FORMATS
        include -= set(exclude or set())

        return {"image/svg+xml": diagram_graph.draw(format="svg").decode("utf-8")}

    # def _ipython_display_(self) -> None:
    #    if not _visual_imports:
    #        raise ImportError("Missing visual imports.")
    #    from IPython.display import SVG
    #
    #    IPython.display.display(SVG(self.show_diagram().draw(format="svg")))

    @staticmethod
    def _add_new_state(state_set: Set[FAStateT], start: int = 0) -> int:
        """Adds new state to the state set and returns it"""
        new_state = start
        while new_state in state_set:
            new_state += 1

        state_set.add(new_state)

        return new_state
