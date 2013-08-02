#!/usr/bin/env python

#
# Load all annotations, and allow iteration through annotation sets
#

import logging
import optparse
import sys

LOG = logging.getLogger(__name__)

slot_types = ["AGENT", "BENEFICIARY", "DEGREE-EXTENT", "EXPERIENCER-PATIENT", "LOCATIVE", "MANNER", "MODAL", "NEGATION", "OTHER", "PURPOSE", "TEMPORAL" ]

# A set of annotations for a sentences
class AnnotationSet:
  def __init__(self,sid,language,segment,number,version,sentence):
    self.sid = sid
    self.language = language
    self.segment = segment
    self.number = number
    self.version = version
    self.sentence = sentence.split() # list of tokens
    self.annotations = []
    # A hypothesis will have a corresponding reference
    # For a reference, this is the sentence itself.
    self.ref_sentence = [] 

  def get_annotators(self):
    return self.annotations.keys()

  def __repr__(self):
    buf = "ANNOTATION SET\n"
    buf += "SENTENCE: sid=%s %s/%s/%s " % (self.sid,self.segment,self.number,self.version)
    buf += " ".join(self.sentence) + "\n"
    for annotation in self.annotations:
      buf += repr(annotation)
      buf += "\n"
    return buf

# Represents an annotated sentence
# if this is a reference, then self.hypothesis will be empty
class Annotation:
  def __init__(self, annotation_set, annotator):
    self.annotation_set = annotation_set
    self.annotator = annotator
    self.reference = [] # list of Frames
    self.hypothesis = [] # list of Frames
    self.action_alignments = []
    self.slot_alignments = []

  def getSentence(self):
    return self.annotation_set.sentence

  def getReferenceSentence(self):
    return self.annotation_set.ref_sentence
  
  def getFrames(self):
    """These are the frames that should be used for IAA"""
    if self.hypothesis:
      return self.hypothesis
    else:
      return self.reference

  def __repr__(self):
    buf = "ANNOTATOR: %s\n" % self.annotator
    buf += "REF FRAMES\n"
    buf += "\n".join([repr(f) for f in self.reference])
    if self.hypothesis:
      buf += "\nHYPO FRAMES\n"
      buf += "\n".join([repr(f) for f in self.hypothesis]) 
      buf += "\nACTION ALIGNS\n\t"
      buf += "\n\t".join([align_text for align_text in sorted(["ALIGN(%s) %s -> %s" % \
        (align.align_type, align.ref_action.getActionString(),\
           align.hyp_action.getActionString())\
              for align in self.action_alignments])])
      buf += "\nSLOT ALIGNS\n\t"
      buf += "\n\t".join([align_text for align_text in sorted(["ALIGN(%s) %s -> %s" % \
        (align.align_type, align.ref_slot.getSlotString(), align.hyp_slot.getSlotString())\
         for align in self.slot_alignments])])
    return buf

class Frame:
  def __init__(self,annotation,action_token,is_reference):
    self.annotation = annotation
    self.action_token = int(action_token)
    self.is_reference = is_reference
    self.slots = []

  def getSentence(self):
    sentence = self.annotation.getSentence()
    if self.is_reference:
      sentence = self.annotation.getReferenceSentence()
    return sentence

  def getActionString(self):
    return self.getSentence()[self.action_token]

  def getActionSpan(self):
    return (self.action_token,self.action_token+1)

  def __repr__(self):
    buf = "ACTION %s\n\t" % self.getActionString()
    buf += "\n\t".join([repr(slot) for slot in sorted(self.slots, key=lambda x: (x.start,x.end))])
    return buf

class Slot:
  def __init__(self,frame,slot_type,start,end):
    self.frame = frame
    self.slot_type = slot_type
    self.start = start
    self.end = end

  def getSlotString(self):
    return " ".join(self.frame.getSentence()[self.start:self.end])

  def getSpan(self):
    return (self.start,self.end)

  def __hash__(self):
    return hash((self.slot_type,self.start,self.end))

  def __eq__(self,other):
    return (self.slot_type,self.start,self.end) == (other.slot_type,other.start,other.end)

  def __repr__(self):
    return "SLOT %s %s (%d,%d)" % (self.slot_type,self.getSlotString(),self.start,self.end) 
     
class ActionAlignment:
  def __init__(self,align_type,ref_action,hyp_action):
    self.ref_action = ref_action
    self.hyp_action = hyp_action
    self.align_type = align_type
      
class SlotAlignment:
  def __init__(self,align_type,ref_slot,hyp_slot):
    self.ref_slot = ref_slot
    self.hyp_slot = hyp_slot
    self.align_type = align_type

def get_raw_data(input_dir, filename):
  """Generator to iterate through the raw data for a given table"""
  fh = open(input_dir + "/" + filename)
  fh.readline()
  for line in fh:
    fields = line[:-1].split("\t")
    yield fields

def load_annotation_sets(input_dir):
  ref_asets = {} # map (language,segment,number) to AnnotationSet
  asets = {} # sid to AnnotationSet
  for sid,language,segment,number,version,text in get_raw_data(input_dir,"sentences_text"):
    aset = AnnotationSet(sid,language,segment,number,version,text)
    asets[sid] = aset
    if version == "00":
      ref_asets[(language,segment,number)] = aset
  return asets,ref_asets


def get_annotations_by_sentence(input_dir):
  """Generator to load sets of annotations for each sentences"""
  #sentences
  asets,ref_asets = load_annotation_sets(input_dir)


  # link hypothesis to their reference sentences
  for aset in asets.values():
    if aset.version != "00":
      aset.ref_sentence = ref_asets[(aset.language,aset.segment,aset.number)].sentence
    else:
      aset.ref_sentence = aset.sentence

  # annotations
  ref_annotations = {} # map ref annotation_id to Annotation,
  hypo_annotations = {} # map hypo annotation_id to Annotation
  hypo_annotation_records = [] # collect them up, for attachment to ref record
  for annotation_id,sid,annotator,ref_id in get_raw_data(input_dir,"annotations"):
    if ref_id == "NULL":
      # ref record
      aset = asets[sid]
      annotation = Annotation(aset, annotator)
      ref_annotations[annotation_id] = annotation
      aset.annotations.append(annotation)
    else:
      hypo_annotation_records.append((annotation_id,sid,annotator,ref_id))
  for annotation_id,sid,annotator,ref_id in hypo_annotation_records:
    annotation = ref_annotations[ref_id]
    hypo_annotations[annotation_id] = annotation
    aset = annotation.annotation_set

  # frames
  frames = {} # map action_id to Frame
  for action_id, annotation_id, tokens in get_raw_data(input_dir, "actions"):
    frame_list = []
    annotation = None
    is_reference = False
    if ref_annotations.has_key(annotation_id):
       annotation = ref_annotations[annotation_id]
       frame_list = annotation.reference
       is_reference = True
    else:
      annotation = hypo_annotations[annotation_id]
      frame_list = annotation.hypothesis
    frame = Frame(annotation,tokens,is_reference)
    frame_list.append(frame)
    frames[action_id] = frame


  # slots
  slots = {} # map slot_id to Slot
  for slot_id,action_id,slot_type,tokens in get_raw_data(input_dir,"slots"):
    frame = frames[action_id]
    tokens = tokens.split(",")
    start,end = int(tokens[0]),int(tokens[-1])+1 # assume comtinuous
    slot = Slot(frame,slot_type,start,end)
    slots[slot_id] = slot
    frame.slots.append(slot)

  # action links
  for align_id,ref_action_id,hypo_action_id,align_type in get_raw_data(input_dir,"action_aligns"):
    ref_action = frames[ref_action_id]
    hypo_action = frames[hypo_action_id]
    align = ActionAlignment(align_type,ref_action,hypo_action)
    hypo_action.annotation.action_alignments.append(align)

  # slot links
  for align_id,ref_slot_id,hypo_slot_id,align_type in get_raw_data(input_dir,"slot_aligns"):
    ref_slot = slots[ref_slot_id]
    hypo_slot = slots[hypo_slot_id]
    align = SlotAlignment(align_type, ref_slot, hypo_slot)
    hypo_slot.frame.annotation.slot_alignments.append(align)


  for aset in sorted(asets.values(),key = lambda x: (x.segment,x.number,x.version,)):
    yield aset

def print_aligns(annotation):
  print "ACTION ALIGNS"
  for align_text in sorted(["\tALIGN(%s) %s -> %s" % \
    (align.align_type, align.ref_action.getActionString(), align.hyp_action.getActionString())\
     for align in annotation.action_alignments]):
    print align_text
  print "SLOT ALIGNS"
  for align_text in sorted(["\tALIGN(%s) %s -> %s" % \
    (align.align_type, align.ref_slot.getSlotString(), align.hyp_slot.getSlotString())\
     for align in annotation.slot_alignments]):
    print align_text
  

def main():
  logging.basicConfig(format='%(levelname)s %(asctime)s %(message)s', datefmt='%Y-%m-%d %H:%M:%S ', level=logging.DEBUG)
  parser = optparse.OptionParser("usage: %prog [options]")
  parser.add_option("-i", "--input-dir", metavar="DIR", dest="input_dir",
    help = "Input directory")
  #parser.add_option("-x", "--exclude-annotators", metavar="ANN", dest="annotator_excludes",
  #  help = "Annotators to exclude", action="append")
  parser.set_defaults(\
    input_dir="./data"
  )
  options,args = parser.parse_args(sys.argv)
  #if not options.annotator_excludes: options.annotator_excludes = ["demo"]
  LOG.debug("Reading annotations from %s" % (options.input_dir))
  for aset in get_annotations_by_sentence(options.input_dir):#, options.annotator_excludes):
    print aset
    sys.stdin.readline()

if __name__ == "__main__":
  main()
