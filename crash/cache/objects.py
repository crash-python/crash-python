#!/usr/bin/env python
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

import intervaltree
import gdb
import crash
from crash.cache import CrashCache
from crash.types.util import safe_lookup_type, addr_cast
from intervaltree import Interval, IntervalTree

objects = intervaltree.IntervalTree()
objects_new = intervaltree.IntervalTree()

ptr_type = gdb.lookup_type("void").pointer()
list_head_type = gdb.lookup_type("struct list_head")

cache_types = dict()
cache_type_candidates = dict()

# avoid calling type_find_pointers repeatedly
type_pointers_cache = dict()

def add_object(addr, size, present, confidence, type_, description):
    begin = long(addr)
    end = begin + size

    # TODO: full overlap, confidence checks...
    for found in objects.search(addr):
        (f_addr, f_end, (f_present, f_conf, f_type, f_desc)) = found
        if f_addr != addr:
            continue
        # FIXME: gdb should do proper type equality!
        if f_type.name == type_.name:
            if f_type != type_:
                print "names match but types not %s %d %s %d" % (f_type.name, f_type.sizeof, type_.name, type_.sizeof)
            # this object is not new
            return;
        else:
            print ("object %x type %s mismatch with already known type %s" %
                        (addr, type_, f_type))

    int_ = Interval(addr, end, (present, confidence, type_, description))
    objects.add(int_)
    objects_new.add(int_)

def add_gdb_object(obj, confidence, description):
    addr = long(obj.address)
    type_ = obj.type
    size = type_.sizeof

    return add_object(addr, size, True, confidence, type_, description)

def type_find_pointers(type_, offset, tree):
    type_ = type_.strip_typedefs()

    if type_.code == gdb.TYPE_CODE_PTR:
        target_type = type_.target().strip_typedefs()
        if target_type.code == gdb.TYPE_CODE_STRUCT:
            # surprised that this comparison works
            if target_type == list_head_type:
#                print "skipping list_head pointer off=%d" % offset
                return
            #TODO: check what those are
            if target_type.sizeof == 0:
                return
            
            tree.addi(offset, offset + type_.sizeof, target_type)
            return
        
    elif type_.code == gdb.TYPE_CODE_ARRAY:
        target_type = type_.target()
        off = offset
        for i in type_.range():
            type_find_pointers(target_type, off, tree)
            off += target_type.sizeof
        return

    if (type_.code != gdb.TYPE_CODE_STRUCT
                            and type_.code != gdb.TYPE_CODE_UNION):
        return

    for field in type_.fields():
        try:
            off = offset + (field.bitpos >> 3)
        except AttributeError, e:
            print ("%s field %s is weird" % (type_, field.name))
        type_find_pointers(field.type, off, tree)

def type_get_pointers(type_):
    name = type_.name
    # FIXME: gdb can't compare Types properly...
    if name is None:
        ptrs = IntervalTree()
        type_find_pointers(type_, 0, ptrs)
        return ptrs
    if name in type_pointers_cache.viewkeys():
        return type_pointers_cache[name]
    ptrs = IntervalTree()
    type_find_pointers(type_, 0, ptrs)
    type_pointers_cache[name] = ptrs
    return ptrs

def process_cache_type(cache, type_):
#    print type_
    if not cache.can_fit_objsize(type_.sizeof):
        print ("size mismatch for type %s (sizeof=%d), and cache %s (%s)" % 
                (type_, type_.sizeof, cache.name, cache.get_sizes_string()))
   
    ptrs = type_get_pointers(type_) 
    cache_types[cache.name] = type_

def kmem_cache_types():
    processed = 0
    found = 0

    cache_type_names = dict()
    unresolved_caches = list()
   
    try: 
        with open("caches") as f:
            for line in f.readlines():
                (cache_name,type_name) = line.rstrip('\n').split(",")
                cache_type_names[cache_name] = type_name
    except IOError, e:
        print "no caches file"
        pass

    for kmem_cache in crash.types.slab.KmemCache.get_all_caches():
        if kmem_cache.is_kmalloc_cache():
            continue
        processed += 1
        cache_name = kmem_cache.name
#        print cache_name

        if cache_name in cache_type_names.viewkeys():
            type_name = cache_type_names[cache_name]
            type_ = safe_lookup_type(type_name)
            if type_ is not None:
                found += 1
                process_cache_type(kmem_cache, type_)
                continue
            else:
                print ("Could not find type '%s' for cache '%s'"
                                % (type_name, cache_name))
                                    
        type_ = safe_lookup_type("struct " + cache_name)
        if type_ is not None:
#            print "FOUND STRUCT TYPE"
            found += 1
            process_cache_type(kmem_cache, type_)
            continue
        type_ = safe_lookup_type(cache_name + "_t")
        if type_ is not None:
#            print "FOUND _t TYPE"
            continue

        print "Could not find type for cache %s" % cache_name
        unresolved_caches.append(cache_name)

    print ("found types for %d of %d caches" % (found, processed))

#    for c in unresolved_caches:
#        print c

#    stupid_search()
    scan_all_objects()

def stupid_search():
    for kmem_cache in crash.types.slab.KmemCache.get_all_caches():
        size = kmem_cache.buffer_size
        for obj in kmem_cache.get_allocated_objects():
            for off in range(0, size, 8):
                tgt = addr_cast(obj + off, ptr_type)
                tgt_addr = long(tgt)
                if not valid_data_ptr(tgt_addr):
                    continue
#                print ("ptr at %x points to %x" % (obj+off, tgt_addr))
                slab = crash.types.slab.Slab.from_obj(tgt_addr)
                if not slab:
                    print ("addr not slab %x" % tgt_addr)
                    continue
                (present, obj_addr, ac) = slab.contains_obj(tgt_addr)
                if not present:
                    continue
                tgt_name = slab.kmem_cache.name
                if kmem_cache.name != tgt_name:
                    print ("found link from cache %s to cache %s"
                                    % (kmem_cache.name, tgt_name))

#TODO unhardcode
def valid_data_ptr(addr):
    if addr >= 0xFFFF880000000000 and addr <= 0xFFFFC7FFFFFFFFFF:
        return True
#    if addr >= 0xFFFFC90000000000 and addr <= 0xFFFFE8FFFFFFFFFF:
#        return True
    return False
        
def scan_object(addr, type_):
    ptrs = type_get_pointers(type_)
    for (off, end, target_type) in ptrs:
        ptr_addr = addr + off
        target_obj = addr_cast(ptr_addr, target_type.pointer()).dereference()
        target_addr = long(target_obj.address)
#        if ptr_addr != target_addr:
#            print ("ptr %x points to %x" % (ptr_addr, target_addr))
        if not valid_data_ptr(target_addr):
            continue
        slab = crash.types.slab.Slab.from_obj(target_addr)
        if not slab:
            continue
        (present, obj_addr, ac) = slab.contains_obj(target_addr)
        if not present:
            print ("found pointer at %x to freed object %x" %
                                            (ptr_addr, obj_addr))
            continue
        #TODO: no pointers to the middle of objects for now
        if obj_addr != target_addr:
            #TODO check if the type at the offset matches
#            add_object(target_addr, target_type.sizeof, True, 0.5, target_type,
#                            "link")
            continue
        cache = slab.kmem_cache
        if cache.is_kmalloc_cache():
#            print ("found ptr of type '%s' to object %x in kmalloc cache %s"
#                                % (target_type, obj_addr, cache.name))
            if target_type.sizeof == 0:
                print ("found ptr of type '%s' to object %x in kmalloc cache %s"
                                % (target_type, obj_addr, cache.name))
                continue
            add_object(obj_addr, target_type.sizeof, True, 0.5, target_type,
                            "link")
            pass
        elif cache.name not in cache_types.viewkeys():
            if cache.name not in cache_type_candidates.viewkeys():
                print ("guessing type of cache %s (%s): %s (sizeof: %d)" %
                    (cache.name, cache.get_sizes_string(),
                                        target_type, target_type.sizeof))
                cache_type_candidates[cache.name] = target_type
            elif target_type.name != cache_type_candidates[cache.name].name:
                print ("cache %s guessed type %s mismatch with existing %s"
                        % (cache.name, target_type, cache_type_candidates[cache.name]))

def scan_kmem_caches(caches):
    for name in caches:
        cache = crash.types.slab.KmemCache.from_name(name)
        type_ = cache_types[name]
        for obj in cache.get_allocated_objects():
            add_object(obj, type_.sizeof, True, 1.0, type_,
                            "allocated in cache '%s'" % name)

#            scan_object(obj, cache, type_)

#    print cache_type_candidates

def process_candidate_caches():
    global cache_type_candidates

    for (name, type_) in cache_type_candidates.viewitems():
        cache = crash.types.slab.KmemCache.from_name(name)
        process_cache_type(cache, type_)

    names = cache_type_candidates.keys()
    cache_type_candidates = dict()
    scan_kmem_caches(names)

def scan_objects(objs):
    for (addr, end, (present, conf, type_, desc)) in objs:
        scan_object(addr, type_)
    
def scan_all_objects():
    global objects_new
    
    scan_kmem_caches(cache_types.viewkeys())

    while len(objects_new) > 0:
        print ("Scanning %d new objects" % len(objects_new))
        objects_to_scan = objects_new
        objects_new = IntervalTree()
        scan_objects(objects_to_scan)
        process_candidate_caches()

    kmalloc_stats()

def kmalloc_stats():
    all_allocated = 0
    all_found = 0
    for cache in crash.types.slab.KmemCache.get_all_caches():
        allocated = 0
        found = 0
        if cache.is_kmalloc_cache():
            for obj in cache.get_allocated_objects():
                allocated += 1
                for int_ in objects.search(obj):
                    (f_addr, f_end, (f_present, f_conf, f_type, f_desc)) = int_
                    if f_addr == obj and f_present == True:
                        found += 1
                        break
            print ("%s: guessed type for %d of %d allocated objects" %
                        (cache.name, found, allocated))
            all_allocated += allocated
            all_found += found

    print ("TOTAL: guessed type for %d of %d (%d %%) allocated objects" %
                    (all_found, all_allocated, all_found * 100 / all_allocated))
    

