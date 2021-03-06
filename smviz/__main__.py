import os
import xml.etree.ElementTree as ET
from graphviz import Digraph
from utils import SMinit
import argparse
from data import *
import sys

"""Object oriented statemachine renderer.
Some Details about the Graphviz API:
The order of commands is quite important.
Any graph that is made a subgraph of another graph needs to be completed. This means that every edge
must be added to the graph and every body modification must be appended BEFORE the subgraph-method is called.
"""


class Statemachine(object):
    """Main class for all Statemachines"""

    def __init__(self, path="", level=0, father=0, filename="", graphname="", rootnode=0, init=0, body=[]):
        super(Statemachine, self).__init__()
        self.pathprefix = path
        self.level = level
        self.father = father
        self.filename = filename
        self.graphname = graphname
        self.rootnode = rootnode
        self.init = init
        self.body = body
        self.inEdges = []
        self.outEdges = []
        self.substatemachines = {}
        self.cmpstates = {}
        self.parallelstates = {}
        self.graph = 0
        self.initialstate = ''
        self.label = ''
        self.translessnodes = []
        self.possiblereturnvalues = []
        self.draw = True
        if level and not len(body):
            if level % 2:
                self.body.append('style=filled')
                self.body.append('color=grey')
            else:
                self.body.append('style=filled')
                self.body.append('color=white')



    init = 0
    """SMinit: contains all the information given by initialisation.
    """

    inEdges = []
    """list[Edge]: Contains all the edges inside the graph.
    """

    outEdges = []
    """list[Edge]: Contains all the edges leading out of the graph.
    """

    substatemachines = {}
    """dict(str, Statemachine) Contains all the Statemachines that are substatemachines of this statemachine, identified by their name.
    """

    cmpstates = {}
    """dict(str, Statemachine) Contains all the Statemachines that represent compound states of this Statemachine, identified by their name.
    """

    parallelstates = {}
    """list[Statemachine] Contains all the Statemachines that represent parallel states of this Statemachine, identified by their name.
    """

    graph = 0
    """Digraph: The graphviz graph resembling this statemachine.
    """

    body = []
    """list(str): Contains all the body options this statemachines graph will use.
    """

    level = 0
    """int: Describes this statemachines level. If a statemachine gets sourced its level will be greater than its parents one.
    """

    pathprefix = ''
    """str: The path in which the file which will be read in lies.
    """

    filename = ''
    """str: The name of the file which will be read in. See pathprefix.
    """

    father = 0
    """Statemachine: The parent of this statemachine. Will only be not 0 if it is sourced by the main Statemachine.
    """

    initialstate = ''
    """str: The initial state of this statemachine.
    """

    label = ''
    """str: The label with which this statemachine will be visualized.
    """

    translessnodes = []  # nodes without transitionevents
    """list(str): A list containing all nodes which have no transition. These nodes will either be the last ones in a \
        statemachine or ones where the statemachines creator unintentionally and mistakenly left out transitions. The \
        later case is to be avoided and thus highlighted in the visualised graph.
    """

    possiblereturnvalues = []
    """list(str): A list containing all possible return values of this statemachine.
    """

    draw = True
    """bool: Defines whether this statemachines graph will be drawn or not.
    """

    rootnode = 0
    """Some kind of ElementTree structure. The root node of this statemachine.
    """

    def addbody(self):
        """Will add all the options in body to this statemachines graph.
        """
        if self.level:
            for option in self.body:
                self.graph.body.append(option)

    def drawiteravly(self):
        """Will draw first all graphs of the substatemachines of this statemachine (recursively) and then this statemachines graph.
        """
        for each in self.substatemachines:
            subst = self.substatemachines[each]
            if subst.draw:
                subst.drawiteravly()
                self.graph.subgraph(subst.graph)
        for each in self.cmpstates:
            cmpst = self.cmpstates[each]
            if cmpst.draw:
                cmpst.drawiteravly()
                self.graph.subgraph(cmpst.graph)
        if self.draw:
            self.drawGraph()

    def drawGraph(self):
        self.inEdges = removeDoubles(self.inEdges)
        self.outEdges = removeDoubles(self.outEdges)
        if self.label:
            self.graph.body.append('label = \"' + self.label + '\"')
        if not self.level:
            self.graph.body.append('label=\"\nSM for ' + self.filename + '\"')
            self.graph.body.append('fontsize=20')
            self.graph.node('Start', shape='Mdiamond')

            tmp = Edge(start='Start')
            if self.initialstate in self.substatemachines and self.init.substrecs > self.level:
                tmp.target = self.substatemachines[self.initialstate].initialstate
            elif self.initialstate in self.cmpstates and not self.init.exclsubst:
                tmp.target = self.cmpstates[self.initialstate].initialstate
            else:
                tmp.target = self.initialstate
            self.addEdge(tmp)

            self.graph.node('Finish', shape='Msquare')
            for each in self.outEdges:
                if not each.target:
                    each.target = 'Finish'
                    each.fontcolor = self.init.sendevntcolor
                self.addEdge(each)
            for each in self.translessnodes:
                each.target = 'Finish'
                each.label = 'unaccounted'
                each.color = 'deeppink'
                each.fontcolor = 'deeppink'
                self.addEdge(each)
        else:
            for each in self.body:
                self.graph.body.append(each)

        if self.father:
            pass

        for each in self.inEdges:
            self.addEdge(each)

    def iterateThroughNodes(self):
        """
        """
        for node in self.rootnode:
            if node.tag.endswith('state'):
                # case: compound state
                if 'initial' in node.attrib:
                    self.handleCmpState(node)
                # case: sourcing of another xml file
                elif 'src' in node.attrib:
                    self.handleSource(node)
                # case: normal node
                else:
                    self.handleNormalState(node)
            #case: parallel state
            elif node.tag.endswith('parallel'):
                self.handleParallel(node)
        self.redirectInitialEdges()

    def redirectInitialEdges(self):
        """ Redirects Edges that are targeted at compound, sourced and parallel states to their respective initial states.
        """
        for edge in self.inEdges:
            target = edge.target
            sm = self
            while detIfComplex(target, sm):
                if detIfComplex(target, sm) == 'cmp':
                    tmp = target
                    target = sm.cmpstates[tmp].initialstate
                    sm = sm.cmpstates[tmp]
                elif detIfComplex(target, sm) == 'subst':
                    tmp = target
                    target = sm.substatemachines[tmp].initialstate
                    sm = sm.substatemachines[tmp]
                elif detIfComplex(target, sm) == 'par':
                    tmp = target
                    target = sm.parallelstates[tmp].initialstate
                    sm = sm.parallelstates[tmp]
            edge.target = target


    def handleCmpState(self, node):
        cmpsmbody = []
        cmpsmbody.append("color=" + self.init.cmpcolor)
        cmpsmbody.append("style=\"\"")
        cmpsm = Statemachine(init=self.init, path=self.pathprefix, level=self.level+1, body=cmpsmbody)
        self.cmpstates[node.attrib['id']] = cmpsm
        cmpsm.father = self
        cmpsm.label = node.attrib['id']
        cmpsm.rootnode = node
        cmpsm.graphname = 'cluster_' + node.attrib['id']
        cmpsm.graph = Digraph(cmpsm.graphname, engine=self.init.rengine, format=self.init.fmt)
        cmpsm.initialstate = node.attrib['initial']

        cmpsm.iterateThroughNodes()

        nodesInCmpsm = []
        for each in node:
            nodesInCmpsm.append(each.attrib['id'])

        edgesToSwitch = []

        for each in cmpsm.inEdges:
            if each.target not in nodesInCmpsm:
                edgesToSwitch.append(each)
        for each in edgesToSwitch:
            cmpsm.inEdges.remove(each)
            cmpsm.outEdges.append(each)

        for each in cmpsm.outEdges:
            if self.init.exclsubst:
                each.start = self.cmpstates[node.attrib['id']].initialstate
                self.inEdges.append(each)
            else:
                if each.target:
                    self.inEdges.append(each)
                else:
                    self.outEdges.append(each)

        if self.init.exclsubst:
            self.graph.node(node.attrib['id'], style="filled")
            cmpsm.draw = False
            for ed in cmpsm.outEdges:
                ed.start = node.attrib['id']

    def handleParallel(self, node):
        pass

    def handleSource(self, node):
        subpath, newfile = splitInPathAndFilename(node.attrib['src'])
        completepath = self.pathprefix + subpath
        newsm = Statemachine(path=completepath, filename=newfile, init=self.init, level=self.level+1)
        self.substatemachines[node.attrib['id']] = newsm
        newsm.father = self
        newsm.graphname = 'cluster_' + newfile
        newsm.label = newfile
        if self.level + 1 >= self.init.substrecs:
            newsm.draw = False
        newsm.readGraph()
        # case: complete subsm will get rendered
        if newsm.draw:
            self.graph.subgraph(newsm.graph)
            for out_edge in newsm.outEdges:
                for propTrans in node:  # propably transitions
                    if propTrans.tag[len(self.init.ns):] == 'transition' and propTrans.attrib['event'] == node.attrib[
                        'id'] + '.' + out_edge.label:
                        # case: send-event
                        if 'target' not in propTrans.attrib:
                            self.outEdges.append(out_edge)
                        # case: normal transition
                        else:
                            out_edge.target = propTrans.attrib['target']
                            out_edge.color = self.init.sendevntcolor
                            self.inEdges.append(out_edge)
                        break
        # case: subsm will be reduced to a single node
        else:
            self.graph.node(node.attrib['id'], style='filled', shape='doublecircle')
            for propTrans in node:
                if propTrans.tag[len(self.init.ns):] == 'transition':
                    if 'target' in propTrans.attrib:
                        ed = Edge()
                        ed.start = node.attrib['id']
                        ed.target = propTrans.attrib['target']
                        ed.label = reduTransEvnt(propTrans.attrib['event'])
                        ed.color = self.init.sendevntcolor
                        self.inEdges.append(ed)
                    else:
                        for send_evnt in propTrans:
                            ed = Edge()
                            ed.start = node.attrib['id']
                            ed.label = sent_evnt.attrib['event']
                            self.outEdges.append(ed)
        self.redirectInitialEdges()

    def handleNormalState(self, node):
        for each in node:
            if each.tag[len(self.init.ns):] == 'transition':
                # case: regular state transition
                if 'target' in each.attrib:
                    ed = Edge()
                    ed.start = node.attrib['id']
                    ed.target = each.attrib['target']
                    if 'cond' in each.attrib:
                        ed.cond = each.attrib['cond']
                    if 'event' in each.attrib:
                        ed.label = reduTransEvnt(each.attrib['event'])
                        ed.color = detEdgeColor(each.attrib['event'], self.init)
                    else:
                        print('Warning: State ' + node.attrib['id'] + ' lacks a event in a transition. Sad.')
                    self.inEdges.append(ed)
                # case: send event transition
                else:
                    for every in each:
                        if every.tag[len(self.init.ns):] == 'send':
                            ed = Edge()
                            ed.start = node.attrib['id']
                            if 'cond' in each.attrib:
                                ed.cond = each.attrib['cond']
                            ed.label = every.attrib['event']
                            self.outEdges.append(ed)
            elif each.tag[len(self.init.ns):] == 'send':#dead code?
                ed = Edge()
                ed.start = node.attrib['id']
                ed.label = each.attrib['event']
                self.possiblereturnvalues.append(ed.label)
                self.outEdges.append(ed)

    def findNodesWithoutNextNode(self):
        nodes = []
        targets = []
        startnodes = []
        for each in self.inEdges:
            if each.target not in targets:
                targets.append(each.target)
                startnodes.append(each.start)
        for each in self.outEdges:
            if each.start not in startnodes:
                startnodes.append(each.start)
        for each in targets:
            if each not in startnodes:
                nodes.append(each)
        return nodes

    def readGraph(self):
        """Reads a graph from a specified filename. Will initialize this statemachines graph as well as its initial state and then call iterateThroughNodes.
        """

        self.graph = Digraph(self.graphname, engine=self.init.rengine, format=self.init.fmt)

        tree = ET.parse(self.pathprefix + self.filename)
        self.rootnode = tree.getroot()
        self.initialstate = self.rootnode.attrib['initial']

        self.iterateThroughNodes()

    def addEdge(self, edge):
        """Will add an Edge to this Graph.

        Args:
            edge: The Edge which will be added.

        Returns:
            Nothing. But will modify the graph of this statemachine.
        """
        labelcond = edge.label
        if edge.cond:
            labelcond = labelcond + ' (' + edge.cond +')'
        self.graph.edge(edge.start, edge.target, color=edge.color, label=labelcond , fontcolor=edge.fontcolor)


# If this script is executed in itself, run the main method (aka generate the graph).
if __name__ == '__main__':
    #TODO: argparsing using argparse
    parser = argparse.ArgumentParser(description='Will render a given statemachine into a .png file (unless otherwise '
                                                 'specified) using GraphViz. Will defautly color regular edges. Edges '
                                                 'containing the words "fatal" or "error" will be rendered red, '
                                                 '"success" green and "Timeout" blue. Furthermore, edges representing '
                                                 '"send events" will have their label rendered blue. Compound states '
                                                 'will either be rendered surrounded by a black border or into a '
                                                 'single, gray state, depending on the "nocmpstates" flag. '
                                                 'Substatemachines will be coloured differently depending on the level '
                                                 'or be reduced into a single, double bordered state.')
    parser.add_argument('--ex')
    parser.add_argument('--reduce')
    parser.add_argument('--nocmpstates')
    parser.add_argument('--cmpstateclr')
    parser.add_argument('--bw')
    parser.add_argument('--eventclr=event:color')
    parser.add_argument('--format')
    parser.add_argument('--savegv')
    parser.add_argument('--gvname')
    parser.add_argument('--rengine')

    init = SMinit()
    init.exclsubst = False
    init.minisg = True
    init.substrecs = 0
    fmt = init.fmt
    inName = init.inputName


    # initialize the switches and stuff
    init.handleArguments(sys.argv)  # check the sanity of the given arguments
    init.sanityChecks()

    p, fn = splitInPathAndFilename(init.inputName)

    sm = Statemachine(path=p, filename=fn, init=init)

    sm.readGraph()

    sm.drawiteravly()

    sm.graph.render(filename=fn[:-4]+'.gv', cleanup=not init.savegv)
    if init.gvname:
        os.rename(fn[:-4] + '.gv.' + fmt, fn[:-4] + '.' + fmt)
    else:
        os.rename(init.gvname + '.' + fmt, fn[:-4] + '.' + fmt)
    sys.exit()
