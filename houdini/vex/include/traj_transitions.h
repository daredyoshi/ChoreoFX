
void addDebugPoint(const int geo; const matrix xform){
    int newpt = addpoint(geo, cracktransform(0,0,0, {0,0,0}, xform));
    setpointattrib(0, "orient", newpt, quaternion(matrix3(xform)));
}

matrix blendXforms(const matrix xform_A; const matrix xform_B; const float weight){
    return slerp(xform_A, xform_B, weight);
    // if(weight == 0.0){
    //     return xform_A;
    // }
    // if(weight == 1.0){
    //     return xform_B;
    // }

    // // split each into trs
    // vector xform_P_A = cracktransform(0, 0, 0, {0,0,0}, xform_A);
    // vector scale_A = cracktransform(0, 0, 2, {0,0,0}, xform_A);
    // vector4 xform_orient_A = quaternion(matrix3(xform_A));

    // vector xform_P_B = cracktransform(0, 0, 0, {0,0,0}, xform_B);
    // vector scale_B = cracktransform(0, 0, 2, {0,0,0}, xform_B);
    // vector4 xform_orient_B = quaternion(matrix3(xform_B));

    // // blend each elemennt
    // vector xform_P = lerp(xform_P_A, xform_P_B, weight);
    // vector4 xform_orient = slerp(xform_orient_A, xform_orient_B, weight);
    // vector xform_scale = lerp(scale_A, scale_B, weight);

    // // reconstruct the matrix
    // matrix xform = qconvert(xform_orient);
    // scale(xform, xform_scale);
    // translate(xform, xform_P);
    // return xform;
}

matrix setXformCol(matrix xform; const int col_idx; const vector col){
    setcomp(xform,   col[0] ,0,col_idx);
    setcomp(xform,   col[1] ,1,col_idx);
    setcomp(xform,   col[2] ,2,col_idx);
    return xform;
}

vector getXformCol(const matrix xform; const int col_idx){
    vector col = set(getcomp(xform, col_idx, 0) ,getcomp(xform, col_idx, 1),getcomp(xform, col_idx, 2));
    return col;
}

// this returns the xform of trajectory B
struct traj_transition_xform{
    // setttings
    int flatten_orient;
    int flatten_pos;
    int auto_first_planted;
    int move_to_start;


    // output
    matrix xform;

    // internal variables (refactor this to make priv)
    int traj_A_geo;
    int traj_B_geo;

    int traj_A_ptnum;
    int traj_B_ptnum;

    int agent_geo;
    int agent_ptnum;
    // in frames
    int transition_len;

    float sync_point;

    int traj_A_start_ptnum; // not the same as in the other struct
    int traj_B_start_ptnum;
    int traj_B_end_ptnum;
    int traj_A_end_ptnum;

    float transition_weight;

    vector P;
    vector4 orient;
    string clipnames [];
    float cliptimes [];
    float clipweights [];
    matrix agentworldtransforms [];

    vector P_A;
    vector4 orient_A;
    string clipnames_A [];
    float cliptimes_A [];
    float clipweights_A [];
    matrix agentworldtransforms_A [];

    vector P_B;
    vector4 orient_B;
    string clipnames_B [];
    float cliptimes_B [];
    float clipweights_B [];
    matrix agentworldtransforms_B [];

    vector P_start;
    vector4 orient_start;
    string clipnames_start [];
    float cliptimes_start [];
    float clipweights_start [];
    matrix agentworldtransforms_start [];

    vector P_end;
    vector4 orient_end;
    string clipnames_end [];
    float cliptimes_end [];
    float clipweights_end [];
    matrix agentworldtransforms_end [];

    float sample_rate;
    string footplantchannels [] ;
    string lowerlimbs [] ;
    vector footoffsets [] ;


    int max_frames_to_check;
    int planted_channel_idx;

    int test [];
    string tests;
    float testf;
    vector testv;

    void init(){
        // settings
        planted_channel_idx = -1; 
        flatten_orient = 1;
        flatten_pos = 1;
        auto_first_planted = 1;
        move_to_start = 1;


        if(traj_A_start_ptnum == -1){
            int numpts_A = npoints(traj_A_geo);

            traj_A_start_ptnum = numpts_A - transition_len ;
            if(transition_len == 0){
                traj_A_start_ptnum = numpts_A - 1;
            }
        }
        if(traj_A_end_ptnum == -1){
            traj_A_end_ptnum = traj_A_start_ptnum + transition_len;
        }
        if(traj_A_ptnum == -1){
            error("Traj A ptnum is required");
        }

        if(traj_B_start_ptnum == -1){
            traj_B_start_ptnum = 0;//int(transition_len * sync_point);   
        } 
        if(traj_B_end_ptnum == -1){
            traj_B_end_ptnum = traj_B_start_ptnum + transition_len;  
        }
        if(traj_B_ptnum == -1){
            traj_B_ptnum = traj_A_ptnum - traj_A_start_ptnum + traj_B_start_ptnum - 1;
        }
        max_frames_to_check=100;
        sample_rate = -1;

        
        // transition_weight = fit(traj_A_ptnum, float(traj_A_start_ptnum) + 0.5, float(traj_A_end_ptnum) + 0.5, 0, 1);
         transition_weight = fit(traj_A_ptnum, float(traj_A_start_ptnum), float(traj_A_end_ptnum), 0, 1);


        P_A = point(traj_A_geo, "P", traj_A_ptnum);
        orient_A = point(traj_A_geo, "orient", traj_A_ptnum);

        clipnames_A = point(traj_A_geo, "clipnames", traj_A_ptnum);
        cliptimes_A = point(traj_A_geo, "cliptimes", traj_A_ptnum);
        clipweights_A = point(traj_A_geo, "clipweights", traj_A_ptnum);
        agentworldtransforms_A = point(traj_A_geo, "agentworldtransforms", traj_A_ptnum);


        P_B = point(traj_B_geo, "P", traj_B_ptnum);
        orient_B = point(traj_B_geo, "orient", traj_B_ptnum);

        clipnames_B = point(traj_B_geo, "clipnames", traj_B_ptnum);
        cliptimes_B = point(traj_B_geo, "cliptimes", traj_B_ptnum);
        clipweights_B = point(traj_B_geo, "clipweights", traj_B_ptnum);
        agentworldtransforms_B = point(traj_B_geo, "agentworldtransforms", traj_B_ptnum);

        P_start = point(traj_A_geo, "P", traj_A_start_ptnum);
        orient_start = point(traj_A_geo, "orient", traj_A_start_ptnum);

        clipnames_start = point(traj_A_geo, "clipnames", traj_A_start_ptnum);
        cliptimes_start = point(traj_A_geo, "cliptimes", traj_A_start_ptnum);
        clipweights_start = point(traj_A_geo, "clipweights", traj_A_start_ptnum);
        agentworldtransforms_A = point(traj_A_geo, "agentworldtransforms", traj_A_start_ptnum);


        P_end = point(traj_B_geo, "P", traj_B_end_ptnum);
        orient_end = point(traj_B_geo, "orient", traj_B_end_ptnum);

        clipnames_end = point(traj_B_geo, "clipnames", traj_B_end_ptnum);
        cliptimes_end = point(traj_B_geo, "cliptimes", traj_B_end_ptnum);
        clipweights_end = point(traj_B_geo, "clipweights", traj_B_end_ptnum);
        agentworldtransforms_end = point(traj_B_geo, "agentworldtransforms", traj_B_end_ptnum);

        // default to A
        xform = qconvert(orient_A, P_A);
        clipnames = clipnames_A;
        cliptimes = cliptimes_A;
        clipweights = clipweights_A;
        agentworldtransforms = agentworldtransforms_A;


        if(!len(footplantchannels) > 0){
            footplantchannels = point(agent_geo, "agentrig_footchannels", agent_ptnum);
            if(!len(footplantchannels) > 0){
                warning(sprintf("Could not find agentrig_footchannels on agent prim geomtetry %d num %i", agent_geo, agent_ptnum));
            }
        }
        if(!len(lowerlimbs) > 0){
            lowerlimbs = point(agent_geo, "agentrig_lowerlimbs", agent_ptnum);
            if(!len(lowerlimbs) > 0){
                warning(sprintf("Could not find agentrig_lowerlimbs on geomtetry %d num %i", agent_geo, agent_ptnum));
            }
        }
        if(!len(footoffsets) > 0){
            footoffsets = point(agent_geo, "agentrig_footoffsets", agent_ptnum);
            if(!len(footoffsets) > 0){
                warning(sprintf("Could not find agentrig_footoffsets on geomtetry %d num %i", agent_geo, agent_ptnum));
            }
        }   

    }
    
    // this returns -1 if no foot was ever planted else it returns the 
    // most recently planted foot. 
    void getBestFootChannelIdx(){
        int planted_channel_idx = -1;
        
        // get if off the clip with the most weight
        float max_clip_weight = 0.0;
        string clipname;
        float cliptime;
        
        if(auto_first_planted == 1){
            foreach(int clip_idx; float clipweight; clipweights_start){
                if(clipweight > max_clip_weight){
                    clipname = clipnames_start[clip_idx];
                    cliptime = cliptimes_start[clip_idx];
                }
            }
            if(clipname == ""){
                error(sprintf("Could not find a clip on trajectory A frame %s", traj_A_start_ptnum));
            }
            
        }
        else if (auto_first_planted == 0){
            foreach(int clip_idx; float clipweight; clipweights_end){
                if(clipweight > max_clip_weight){
                    clipname = clipnames_end[clip_idx];
                    cliptime = cliptimes_end[clip_idx];
                }
            }
            if(clipname == ""){
                error(sprintf("Could not find a clip on trajectory B frame %s", traj_B_end_ptnum));
            }

        }

        
        sample_rate = agentclipsamplerate(agent_geo, agent_ptnum, clipname);

        // for each limb
        // figure out the most recently planted foot and take that
        int least_frames_since_planted = 100;
        foreach(int test_planted_channel_idx; string footchannel_name; footplantchannels){
            // for each channel
            int limb_idx = floor(test_planted_channel_idx / 2);
            float planted =agentclipsample(agent_geo, agent_ptnum, clipname, cliptime, footchannel_name);

            // find out how long this channel has been planted
            int frames_to_subtract = 0;
            int planted_found = 0;
            
            float check_time;
            // check backwards for planted frames 
            for(frames_to_subtract; frames_to_subtract < max_frames_to_check; frames_to_subtract++){
                check_time = cliptime - sample_rate * frames_to_subtract;
                float check_planted =agentclipsample(agent_geo, agent_ptnum, clipname, check_time, footchannel_name);
                testf = check_planted;
                if(check_planted > 0.1){
                    planted_found = 1;
                    break;
                }
            }
            // get the last planted foot
            if(frames_to_subtract < least_frames_since_planted && planted_found == 1){
                // fuck side fx for not having a linear mapping between foot channels and lower limbs
                planted_channel_idx = test_planted_channel_idx;
                least_frames_since_planted = frames_to_subtract;
            }            
        }


        // planted_channel_idx = -1;


        // string all_clipnames [] = clipnames_start;
        // append(all_clipnames, clipnames_end);
        // float all_cliptimes [] = array();
        // // this makes it easier to offest because we can subtract from both
        // foreach(float cliptime; cliptimes_start){
        //     append(all_cliptimes, cliptime + transition_len * sample_rate);
        // }
        // append(all_cliptimes, cliptimes_end);
        // float all_clipweights [] = clipweights_start;
        // append(all_clipweights, clipweights_end);
        // float all_scores [] = array();        

        // // for each clip add all the scores for each index together
        // foreach(int clip_idx; string clipname; all_clipnames){
        //     sample_rate = agentclipsamplerate(agent_geo, agent_ptnum, clipname);

        //     float cliptime = all_cliptimes[clip_idx];
        //     float clipweight = all_clipweights[clip_idx];
        //     // for each limb
        //     // figure out which limb is planted the most for both clips during the transition
        //     int least_frames_since_planted = 100;
        //     foreach(int planted_channel_idx; string footchannel_name; footplantchannels){
        //         // for each channel
        //         int limb_idx = floor(planted_channel_idx / 2);

        //         // find out how long this channel has been planted
        //         float check_time;
        //         // check backwards for planted frames 
        //         for(int frame_to_subtract = 0; frame_to_subtract < transition_len; frame_to_subtract++){
        //             float weight = fit(frame_to_subtract, 0, transition_len, 0, 1);
        //             //weight = 1.0;
        //             // remember that start is the other way around
        //             if(clip_idx > len(clipnames_start)){
        //                     weight = 1.0 - weight;
        //             }


        //             check_time = cliptime - sample_rate * frame_to_subtract;
        //             float check_planted =agentclipsample(agent_geo, agent_ptnum, clipname, check_time, footchannel_name);
        //             all_scores[planted_channel_idx] += check_planted * clipweight * weight;
        //         }    
        //     }
        // }
        // // printf("\nall scores = %s", all_scores);
        // int sorted_channel_idxs [] = argsort(all_scores);
        // planted_channel_idx = sorted_channel_idxs[0];

    }

    // this returns the xform of the agent
    // if a best_foot_channel exists it translates the agent xform by that position
    // this assumes that clipweights are normalized
    matrix getXform(const vector _P ; const vector4 _orient; const string _clipnames []; 
        const float _cliptimes []; const float _clipweights []; const int _planted_channel_idx){
        matrix _xform= qconvert(_orient, _P);

        // the only possible way is if there never was anythign planted
        if(_planted_channel_idx != -1){
            // get the actual blended transforms
            matrix agenttransforms [] = array();
            // get the lerped world transforms at the current time for A and B
            // we are re-creating what _cliptimes would be doing
            foreach(int clip_idx; string clipname; _clipnames){
                float clipweight = _clipweights[clip_idx];
                float cliptime = _cliptimes[clip_idx];
                matrix clip_local_transforms [] = agentclipsamplelocal(agent_geo, agent_ptnum, clipname, cliptime);


                foreach(int xform_idx; matrix curr; clip_local_transforms){
                    if(clip_idx == 0){
                        agenttransforms[xform_idx] = curr;
                    }
                    else{
                        matrix prev = agenttransforms[xform_idx];
                        matrix blended = blendXforms(prev, curr, clipweight);
                        agenttransforms[xform_idx] = blended;
                    }
                    
                }
            }
            agenttransformtoworld(agent_geo, agent_ptnum, agenttransforms);





            // get the desired xform of traj A
            int lowerlimb_idx = 2 + (_planted_channel_idx % 2) + (floor(_planted_channel_idx / 2) * 4);

            string foot_channel_name = lowerlimbs[lowerlimb_idx];
            vector foot_channel_offset = footoffsets[_planted_channel_idx];

            int foot_channel_rig_idx = agentrigfind(agent_geo, agent_ptnum, foot_channel_name);
            matrix foot_xform =agenttransforms[foot_channel_rig_idx];

            foot_channel_offset *=foot_xform;
            translate(foot_xform, foot_channel_offset - cracktransform(0,0,0,{0,0,0}, foot_xform) );
            matrix rescaled_foot_xform = matrix(qconvert(quaternion(matrix3(foot_xform))));
            translate(rescaled_foot_xform, cracktransform(0,0,0,{0,0,0}, foot_xform));

            
            rescaled_foot_xform *= _xform;
            _xform = rescaled_foot_xform;
        }

        if(flatten_orient){
            // transform the xform so it only take the z from the orient
            // matrix3 rot = matrix3(_xform);
            vector new_y = set(0, 1, 0);
            _xform = setXformCol(_xform, 1, new_y);
            vector new_z = normalize(getXformCol(_xform, 2));
            new_z[1] = 0;
            new_z = normalize(new_z);
            _xform = setXformCol(_xform, 2, new_z);
            vector new_x = cross(new_z, new_y);
            vector curr_x = getXformCol(_xform, 0);
            // to prevent flipping in case the new x is the wrong side
            // cross can go either way so use dot to see 
            // if it's the right order

            float dot_xz = dot(cross(new_x, new_y), new_z);

            if(dot_xz >= 0.0){
                new_x = cross(new_y, new_z);
            }
            

            _xform = setXformCol(_xform, 0, new_x);
        }
        if(flatten_pos){
            //set the y to 0
            setcomp(_xform, 0.0, 3, 1 );
        }

 
        return _xform;
    }

    matrix getXform(const vector _P ; const vector4 _orient; const string _clipnames []; 
        const float _cliptimes []; const float _clipweights []){
        return this->getXform(_P, _orient, _clipnames, _cliptimes, _clipweights, -1);
    }

    void blend(){

        // only blend transforms if necessary
        // these will get converted to local for blending
        matrix agenttransforms_A [] = agentworldtransforms_A;
        matrix agenttransforms_B [] = agentworldtransforms_B;
        // if(len(agenttransforms_A)>0 ){
            // transform to local for lerping in parent space
        matrix temp_agenttransforms [] = array();
        agenttransformtolocal(agent_geo, agent_ptnum, agenttransforms_A);
        agenttransformtolocal(agent_geo, agent_ptnum, agenttransforms_B);
        foreach(int idx; matrix xform_A; agenttransforms_A){
            matrix xform_B = agenttransforms_B[idx];
            matrix xform = blendXforms(xform_A, xform_B, transition_weight);
            append(temp_agenttransforms, xform);
        }
        agenttransformtoworld(agent_geo, agent_ptnum, temp_agenttransforms);
        agentworldtransforms = temp_agenttransforms;
        // }

        // get the transition clip weights
        float new_clip_weights [] = array();
        foreach(float clip_weight; clipweights_A){
            append(new_clip_weights, clip_weight *(1 - transition_weight));
        }
        foreach(float clip_weight; clipweights_B){
            append(new_clip_weights, clip_weight * transition_weight);
        }
        clipweights = new_clip_weights;
        
        // set generic attribs
        string new_clipnames [] = clipnames_A;
        foreach(string clipname; clipnames_B){
            append(new_clipnames, clipname);
        }
        clipnames = new_clipnames;

        float new_cliptimes [] = cliptimes_A;
        foreach(float cliptime;  cliptimes_B){
            append(new_cliptimes, cliptime);
        }
        cliptimes = new_cliptimes;

    }

    
    void blendXform(){

        matrix xform_start = this->getXform(P_start, orient_start, clipnames_start, cliptimes_start, clipweights_start); 
        matrix xform_end = this->getXform(P_end, orient_end, clipnames_end, cliptimes_end, clipweights_end); 


        if(traj_A_ptnum > traj_A_start_ptnum && traj_A_ptnum <= traj_A_end_ptnum){

            matrix xform_A = this->getXform(P_A, orient_A, clipnames, cliptimes, clipweights); 
            matrix xform_B = this->getXform(P_B, orient_B, clipnames, cliptimes, clipweights); 
            matrix blend_xform =blendXforms(xform_A, xform_B,  transition_weight );
            xform = invert(xform_B) * blend_xform   ;
        }
        else{
            xform = ident();
        }
    }

    void linearTransition(){
        this->blend();
        this->blendXform();
    }

    void plantedXform(){

        // if it's set to auto gurantee there's a channel
        if(planted_channel_idx < 0){
            this->getBestFootChannelIdx();
        }
        this->blend();
 

        matrix xform_start = this->getXform(P_start, orient_start, clipnames_start, cliptimes_start, clipweights_start); 
        matrix xform_start_planted = this->getXform(P_start, orient_start, clipnames_start, cliptimes_start, clipweights_start, planted_channel_idx); 

        matrix xform_end = this->getXform(P_end, orient_end, clipnames_end, cliptimes_end, clipweights_end); 
        matrix xform_end_planted = this->getXform(P_end, orient_end, clipnames_end, cliptimes_end, clipweights_end, planted_channel_idx); 

        if(traj_A_ptnum > traj_A_start_ptnum && traj_A_ptnum <= traj_A_end_ptnum){
            xform_end= this->getXform(P_B, orient_B, clipnames, cliptimes, clipweights); 
            xform_end_planted = this->getXform(P_B, orient_B, clipnames, cliptimes, clipweights, planted_channel_idx); 
         }

        matrix xform_start_end_diff = xform_start *  invert(xform_end * xform_start);

        matrix xform_start_planted_0 = xform_start_planted * invert(xform_start);
        matrix xform_end_planted_0 = xform_end_planted * invert(xform_end);

        matrix xform_offset = invert(xform_end_planted_0) * xform_start_planted_0;
        xform = xform_start_end_diff * xform_offset * xform_start;

        // addDebugPoint(0, xform_offset);
    }


    

    void plantedTransition(){
        //if it's set to auto gurantee there's a channel
        if(planted_channel_idx < 0){
            this->getBestFootChannelIdx();
        }
        // this->blend();
        this->plantedXform(); // this also calls blend
    }
}






