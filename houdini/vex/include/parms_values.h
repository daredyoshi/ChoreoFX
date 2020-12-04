/*
These are utility function for common parm reading operations
*/


/*
Many of our uis have the option to randomize on a per-point level
these options include the possibility of randomizing between
two values, which can also be distributed along a ramp.
You also have the option to multiply by an incoming float attribute
this assumes all the parms are named as follows

prefix_do_randomize_suffix  enable randomization of this value between min and max
prefix_mult_attrib_suffix   enable the multiplication of this value by an incoming float attribute
prefix_suffix               if not randomizing use this as the value (could still get multiplied by attrib)
prefix_attrib_suffix        the name of the float point attribute by which to multiple the value
prefix_do_ramp_suffix       set the distribution of the value between min (0) and max(1)
prefix_min_suffix           the minimum value to use when randomizing
prefix_max_suffix           the maximum value to use when randomizing

The arguments of the function are
int seed                    the seed of the randomization (usually based off @ptnum)
string parm_prefix          the prefix of the parm to use (e.g. ../offset_) DON'T FORGET THE NODE PATH
string parm_suffix          the suffix of the parm to us (e.g. _1 if in multiplarm block)
*/
float getFloatRandParmPtVal(const int seed; const int geo; const int ptnum;
const string parm_prefix; const string parm_suffix
){
    //return value
    float value;
    int do_randomize = chi(parm_prefix + "_do_randomize_" + parm_suffix);

    if(do_randomize){
        value = rand(seed);
        int do_ramp = chi(parm_prefix + "_do_ramp_" + parm_suffix);
        if(do_ramp){
            value = chramp(parm_prefix + "_ramp_" + parm_suffix, value);
        }

        float min = ch(parm_prefix + "_min_" + parm_suffix);
        float max = ch(parm_prefix + "_max_" + parm_suffix);

        value = fit01(value, min, max);
    }
    else{

        value = ch(parm_prefix + "_" + parm_suffix);
    }

    // attrib multiplication
    int mult_attrib = chi(parm_prefix + "_mult_attrib_" + parm_suffix);
    if(mult_attrib){
        string attrib_name = chs(parm_prefix + "_attrib_" + parm_suffix);
        int has_attrib = haspointattrib(geo, attrib_name);
        if(has_attrib){
            float attrib_val = point(geo, attrib_name, ptnum);
            value *= attrib_val;
        }
        else{
            string msg = sprintf("Attrib %s for multiplying %g not found on input points",
                attrib_name,
                parm_prefix + "_" + parm_suffix
            );
            error(msg);
        }
    }
    return value;
}

/*
This is a function designed to force us to use a cosistent
parm name and agent_id. We could abstract those, but it would be better
if it was impossible for those to change. It checks to see
if a global seed channel exsist as well as if there is an agent_id
point attribute.

If ether of those are false it errors.

If not it will return a convenient seed.
*/
int getSeedAgentId(const int geo; const int ptnum){
    //check if global seed channel exists
    int opid;
    int parm_idx;
    int vec_idx;
    string agent_id_attrib_name = "agent_id";

    chid("../global_seed", opid, parm_idx, vec_idx);
    if(opid == -1){
        error("No channel ../global_seed found");
        return -1;
    }
    int global_seed = chi("../global_seed");

    // check if agent_id attrib exists
    int has_agent_id = haspointattrib(geo, agent_id_attrib_name);
    if(!has_agent_id){
        error("No agent_id point attribute found");
        return -1;
    }
    int agent_id = point(geo, agent_id_attrib_name, ptnum);

    return global_seed + agent_id + 666;

}

/*

The prefix and suffix include _ chars unlike the getFloatRandParmPtVal
*/

function int [] getMultiParmValues(const string prefix; const string suffix; const int amount; const int start_idx){
    // return value
    int vals [];
    for(int i = start_idx; i<amount + start_idx; i++){
        int value = chi(prefix + itoa(i) + suffix);
        append(vals, value);
    }
    return vals;
}

function int [] getMultiParmValues(const string prefix; const string suffix; const int amount){
    // default to a start_idx of 1
    int start_idx = 1;
    return getMultiParmValues(prefix, suffix, amount, start_idx);
}

function float [] getMultiParmValues(const string prefix; const string suffix; const int amount; const int start_idx){
    // return value
    float vals [];
    for(int i = start_idx; i<amount + start_idx; i++){
        float value = ch(prefix + itoa(i) + suffix);
        append(vals, value);
    }
    return vals;
}

function float [] getMultiParmValues(const string prefix; const string suffix; const int amount){
    int start_idx = 1;
    return getMultiParmValues(prefix, suffix, amount, start_idx);
}

function string [] getMultiParmValues(const string prefix; const string suffix; const int amount; const int start_idx){
    // return value
    string vals [];
    for(int i = start_idx; i<amount + start_idx; i++){
        string value = chs(prefix + itoa(i) + suffix);
        append(vals, value);
    }
    return vals;
}

function string [] getMultiParmValues(const string prefix; const string suffix; const int amount){
    int start_idx = 1;
    return getMultiParmValues(prefix, suffix, amount, start_idx);
}

