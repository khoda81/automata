#!/usr/bin/env python3
"""Classes and methods for working with all finite automata."""

import abc
import itertools
import os
import pathlib
import typing
import uuid
from collections import defaultdict

import graphviz
from coloraide import Color

from automata.base.automaton import Automaton, AutomatonStateT

FAStateT = AutomatonStateT


class FA(Automaton, metaclass=abc.ABCMeta):
    """An abstract base class for finite automata."""

    __slots__ = tuple()

    @staticmethod
    def get_state_label(state_data):
        """
        Get an string representation of a state. This is used for displaying and
        uses `str` for any unsupported python data types.
        """
        if isinstance(state_data, str):
            if state_data == "":
                return "λ"

            return state_data

        if isinstance(state_data, (set, frozenset, list, tuple)):
            inner = ", ".join(FA.get_state_label(sub_data) for sub_data in state_data)
            if isinstance(state_data, (set, frozenset)):
                if state_data:
                    return "{" + inner + "}"
                else:
                    return "∅"

            if isinstance(state_data, tuple):
                return "(" + inner + ")"

            if isinstance(state_data, list):
                return "[" + inner + "]"

        return str(state_data)

    @abc.abstractmethod
    def iter_states(self):
        """Iterate over all states in the automaton."""

    @abc.abstractmethod
    def iter_transitions(self):
        """
        Iterate over all transitions in the automaton. Each transition is a tuple
        of the form (from_state, to_state, symbol)
        """

    @abc.abstractmethod
    def is_accepting(self, state):
        """Check if a state is an accepting state."""

    @abc.abstractmethod
    def is_initial(self, state):
        """Check if a state is an initial state."""

    def show_diagram(
        self,
        input_str: str | None = None,
        save_path: str | os.PathLike | None = None,
        *,
        engine: typing.Optional[str] = None,
        view=False,
        cleanup: bool = True,
        horizontal: bool = True,
        reverse_orientation: bool = False,
        fig_size: tuple = None,
        font_size: float = 14.0,
        arrow_size: float = 0.85,
        state_separation: float = 0.5,
    ):
        """
        Generates the graph associated with the given DFA.
        Args:
            input_str (str, optional): String list of input symbols. Defaults to None.
            - save_path (str or os.PathLike, optional): Path to output file. If
              None, the output will not be saved.
            - path (str, optional): Folder path for output file. Defaults to
              None.
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

        # Defining the graph.
        graph = graphviz.Digraph(strict=False, engine=engine)

        # TODO test fig_size
        if fig_size is not None:
            graph.attr(size=", ".join(map(str, fig_size)))

        graph.attr(ranksep=str(state_separation))
        font_size = str(font_size)
        arrow_size = str(arrow_size)

        if horizontal:
            graph.attr(rankdir="LR")
        if reverse_orientation:
            if horizontal:
                graph.attr(rankdir="RL")
            else:
                graph.attr(rankdir="BT")

        for state in self.iter_states():
            # every edge needs an origin node, so we add a null node for every
            # initial state.
            if self.is_initial(state):
                # we use a random uuid to make sure that the null node has a
                # unique id to avoid colliding with other states and null_nodes.
                null_node = str(uuid.uuid4())
                graph.node(
                    null_node,
                    label="",
                    tooltip=".",
                    shape="point",
                    fontsize=font_size,
                )
                node = self.get_state_label(state)
                graph.edge(
                    null_node,
                    node,
                    tooltip="->" + node,
                    arrowsize=arrow_size,
                )

        for state in self.iter_states():
            shape = "doublecircle" if self.is_accepting(state) else "circle"
            node = self.get_state_label(state)
            graph.node(node, shape=shape, fontsize=font_size)

        is_edge_drawn = defaultdict(lambda: False)
        if input_str is not None:
            path, is_accepted = self._get_input_path(input_str=input_str)

            start_color = Color("#FFFF00")
            end_color = Color("#00FF00") if is_accepted else Color("#FF0000")

            number_of_colors = len(input_str)
            interpolation = Color.interpolate([start_color, end_color], space="lch")
            colors = (
                interpolation(x / number_of_colors) for x in range(number_of_colors + 1)
            )

            # Define all transitions in the finite state machine with traversal.
            for transition_index, (color, transitions) in enumerate(
                zip(colors, path), start=1
            ):
                for from_state, to_state, symbol in transitions:
                    is_edge_drawn[from_state, to_state, symbol] = True

                    from_node = self.get_state_label(from_state)
                    to_node = self.get_state_label(to_state)
                    label = self.get_edge_label(symbol)
                    graph.edge(
                        from_state,
                        to_state,
                        label=" [#{}]\n{} ".format(transition_index, symbol),
                        arrowsize=arrow_size,
                        fontsize=font_size,
                        color=color.to_string(hex=True),
                        penwidth="2.5",
                    )

        edge_labels = defaultdict(list)
        for from_state, to_state, symbol in self.iter_transitions():
            if is_edge_drawn[from_state, to_state, symbol]:
                continue

            label = self.get_edge_label(symbol)
            from_node = self.get_state_label(from_state)
            to_node = self.get_state_label(to_state)
            edge_labels[from_node, to_node].append(label)

        for (from_node, to_node), labels in edge_labels.items():
            label = ",".join(sorted(labels))
            graph.edge(
                from_node,
                to_node,
                label=label,
                arrowsize=arrow_size,
                fontsize=font_size,
            )

        # Write diagram to file. PNG, SVG, etc.
        if save_path is not None:
            save_path: pathlib.Path = pathlib.Path(save_path)

            directory = save_path.parent
            directory.mkdir(parents=True, exist_ok=True)
            filename = save_path.stem
            format = save_path.suffix.split(".")[1] if save_path.suffix else None

            graph.render(
                directory=directory,
                filename=filename,
                format=format,
                cleanup=cleanup,
                view=view,
            )

        elif view:
            graph.render(view=True)

        return graph

    def get_edge_label(self, symbol):
        return str(symbol)

    def _get_input_path(self, input_str):
        raise NotImplementedError(
            f"_get_input_path is not implemented for {self.__class__}"
        )

    def _ipython_display_(self):
        # IPython is imported here because this function is only called by
        # IPython. So if IPython is not installed, this function will not be
        # called, therefore no need to add ipython as dependency.
        from IPython.display import display

        display(self.show_diagram())
