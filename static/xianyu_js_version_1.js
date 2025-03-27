const crypto = require('crypto')

const generate_mid = () => {
    return "" + Math.floor(1e3 * Math.random()) + new Date().getTime() + " 0"
}

const generate_uuid = () => {
    return "-" + Date.now() + "1"
}

const generate_device_id = (user_id) => {
    for (var ee, et = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz".split(""), en = [], eo = Math.random, ei = 0; ei < 36; ei++)
        8 === ei || 13 === ei || 18 === ei || 23 === ei ? en[ei] = "-" : 14 === ei ? en[ei] = "4" : (ee = 0 | 16 * eo(),
        en[ei] = et[19 === ei ? 3 & ee | 8 : ee]);
    return en.join("") + "-" + user_id
}


const generate_sign = (t ,token, data) => {
    const j = t
    const h = 34839810
    const msg = token + "&" + j + "&" + h + "&" + data
    const md5 = crypto.createHash('md5')
    md5.update(msg)
    return md5.digest('hex')
}



rA = 0;
rB = 0;
ed = [];
eu = undefined
rj = {
    "useRecords": false,
    "mapsAsObjects": true
}
ei = new TextDecoder("utf-8");
eh = undefined;
ec = undefined;
function rK() {
    var ee, et = ec[rA++];
    if (et < 160) {
        if (et < 128) {
            if (et < 64)
                return et;
            var en = ed[63 & et] || rj.getStructures && rQ()[63 & et];
            return en ? (en.read || (en.read = rY(en, 63 & et)),
                en.read()) : et
        }
        if (et < 144) {
            if (et -= 128,
                rj.mapsAsObjects) {
                for (var eo = {}, ei = 0; ei < et; ei++) {
                    var em = ol();
                    "__proto__" === em && (em = "__proto_"),
                        eo[em] = rK()
                }
                return eo
            }
            for (var ev = new Map, eg = 0; eg < et; eg++)
                ev.set(rK(), rK());
            return ev
        }
        for (var eC = Array(et -= 144), eS = 0; eS < et; eS++)
            eC[eS] = rK();
        return rj.freezeData ? Object.freeze(eC) : eC
    }
    if (et < 192) {
        var ew = et - 160;
        if (rB >= rA)
            return ef.slice(rA - rF, (rA += ew) - rF);
        if (0 == rB && eu < 140) {
            var ek = ew < 16 ? on(ew) : ot(ew);
            if (null != ek)
                return ek
        }
        return r0(ew)
    }
    switch (et) {
        case 192:
            return null;
        case 193:
            if (ep) {
                if ((ee = rK()) > 0)
                    return ep[1].slice(ep.position1, ep.position1 += ee);
                return ep[0].slice(ep.position0, ep.position0 -= ee)
            }
            return rH;
        case 194:
            return !1;
        case 195:
            return !0;
        case 196:
            if (void 0 === (ee = ec[rA++]))
                throw Error("Unexpected end of buffer");
            return oo(ee);
        case 197:
            return ee = eh.getUint16(rA),
                rA += 2,
                oo(ee);
        case 198:
            return ee = eh.getUint32(rA),
                rA += 4,
                oo(ee);
        case 199:
            return oi(ec[rA++]);
        case 200:
            return ee = eh.getUint16(rA),
                rA += 2,
                oi(ee);
        case 201:
            return ee = eh.getUint32(rA),
                rA += 4,
                oi(ee);
        case 202:
            if (ee = eh.getFloat32(rA),
            rj.useFloat32 > 2) {
                var eE = oC[(127 & ec[rA]) << 1 | ec[rA + 1] >> 7];
                return rA += 4,
                (eE * ee + (ee > 0 ? .5 : -.5) >> 0) / eE
            }
            return rA += 4,
                ee;
        case 203:
            return ee = eh.getFloat64(rA),
                rA += 8,
                ee;
        case 204:
            return ec[rA++];
        case 205:
            return ee = eh.getUint16(rA),
                rA += 2,
                ee;
        case 206:
            return ee = eh.getUint32(rA),
                rA += 4,
                ee;
        case 207:
            return "number" === rj.int64AsType ? ee = 4294967296 * eh.getUint32(rA) + eh.getUint32(rA + 4) : "string" === rj.int64AsType ? ee = eh.getBigUint64(rA).toString() : "auto" === rj.int64AsType ? (ee = eh.getBigUint64(rA)) <= BigInt(2) << BigInt(52) && (ee = Number(ee)) : ee = eh.getBigUint64(rA),
                rA += 8,
                ee;
        case 208:
            return eh.getInt8(rA++);
        case 209:
            return ee = eh.getInt16(rA),
                rA += 2,
                ee;
        case 210:
            return ee = eh.getInt32(rA),
                rA += 4,
                ee;
        case 211:
            return "number" === rj.int64AsType ? ee = 4294967296 * eh.getInt32(rA) + eh.getUint32(rA + 4) : "string" === rj.int64AsType ? ee = eh.getBigInt64(rA).toString() : "auto" === rj.int64AsType ? (ee = eh.getBigInt64(rA)) >= BigInt(-2) << BigInt(52) && ee <= BigInt(2) << BigInt(52) && (ee = Number(ee)) : ee = eh.getBigInt64(rA),
                rA += 8,
                ee;
        case 212:
            if (114 == (ee = ec[rA++]))
                return od(63 & ec[rA++]);
            var e_ = rz[ee];
            if (e_) {
                if (e_.read)
                    return rA++,
                        e_.read(rK());
                if (e_.noBuffer)
                    return rA++,
                        e_();
                return e_(ec.subarray(rA, ++rA))
            }
            throw Error("Unknown extension " + ee);
        case 213:
            if (114 == (ee = ec[rA]))
                return rA++,
                    od(63 & ec[rA++], ec[rA++]);
            return oi(2);
        case 214:
            return oi(4);
        case 215:
            return oi(8);
        case 216:
            return oi(16);
        case 217:
            if (ee = ec[rA++],
            rB >= rA)
                return ef.slice(rA - rF, (rA += ee) - rF);
            return r3(ee);
        case 218:
            if (ee = eh.getUint16(rA),
                rA += 2,
            rB >= rA)
                return ef.slice(rA - rF, (rA += ee) - rF);
            return r4(ee);
        case 219:
            if (ee = eh.getUint32(rA),
                rA += 4,
            rB >= rA)
                return ef.slice(rA - rF, (rA += ee) - rF);
            return r5(ee);
        case 220:
            return ee = eh.getUint16(rA),
                rA += 2,
                r8(ee);
        case 221:
            return ee = eh.getUint32(rA),
                rA += 4,
                r8(ee);
        case 222:
            return ee = eh.getUint16(rA),
                rA += 2,
                r7(ee);
        case 223:
            return ee = eh.getUint32(rA),
                rA += 4,
                r7(ee);
        default:
            if (et >= 224)
                return et - 256;
            if (void 0 === et) {
                var eT = Error("Unexpected end of MessagePack data");
                throw eT.incomplete = !0,
                    eT
            }
            throw Error("Unknown MessagePack token " + et)
    }
}

function r6(ee) {
    if (ee < 16 && (et = on(ee)))
        return et;
    if (ee > 64 && ei)
        return ei.decode(ec.subarray(rA, rA += ee));
    var et, en = rA + ee, eo = [];
    for (et = ""; rA < en;) {
        var eu = ec[rA++];
        if ((128 & eu) === 0)
            eo.push(eu);
        else if ((224 & eu) === 192) {
            var ed = 63 & ec[rA++];
            eo.push((31 & eu) << 6 | ed)
        } else if ((240 & eu) === 224) {
            var ef = 63 & ec[rA++]
                , ep = 63 & ec[rA++];
            eo.push((31 & eu) << 12 | ef << 6 | ep)
        } else if ((248 & eu) === 240) {
            var em = (7 & eu) << 18 | (63 & ec[rA++]) << 12 | (63 & ec[rA++]) << 6 | 63 & ec[rA++];
            em > 65535 && (em -= 65536,
                eo.push(em >>> 10 & 1023 | 55296),
                em = 56320 | 1023 & em),
                eo.push(em)
        } else
            eo.push(eu);
        eo.length >= 4096 && (et += r9.apply(String, eo),
            eo.length = 0)
    }
    return eo.length > 0 && (et += r9.apply(String, eo)),
        et
}

r0 = r6;
r4 = r6;
var r9 = String.fromCharCode;
function on(ee) {
    if (ee < 4) {
        if (ee < 2) {
            if (0 === ee)
                return "";
            var et = ec[rA++];
            if ((128 & et) > 1) {
                rA -= 1;
                return
            }
            return r9(et)
        }
        var en = ec[rA++]
            , eo = ec[rA++];
        if ((128 & en) > 0 || (128 & eo) > 0) {
            rA -= 2;
            return
        }
        if (ee < 3)
            return r9(en, eo);
        var ei = ec[rA++];
        if ((128 & ei) > 0) {
            rA -= 3;
            return
        }
        return r9(en, eo, ei)
    }
    var eu = ec[rA++]
        , ed = ec[rA++]
        , ef = ec[rA++]
        , ep = ec[rA++];
    if ((128 & eu) > 0 || (128 & ed) > 0 || (128 & ef) > 0 || (128 & ep) > 0) {
        rA -= 4;
        return
    }
    if (ee < 6) {
        if (4 === ee)
            return r9(eu, ed, ef, ep);
        var em = ec[rA++];
        if ((128 & em) > 0) {
            rA -= 5;
            return
        }
        return r9(eu, ed, ef, ep, em)
    }
    if (ee < 8) {
        var eh = ec[rA++]
            , ev = ec[rA++];
        if ((128 & eh) > 0 || (128 & ev) > 0) {
            rA -= 6;
            return
        }
        if (ee < 7)
            return r9(eu, ed, ef, ep, eh, ev);
        var eg = ec[rA++];
        if ((128 & eg) > 0) {
            rA -= 7;
            return
        }
        return r9(eu, ed, ef, ep, eh, ev, eg)
    }
    var eC = ec[rA++]
        , eS = ec[rA++]
        , ew = ec[rA++]
        , ek = ec[rA++];
    if ((128 & eC) > 0 || (128 & eS) > 0 || (128 & ew) > 0 || (128 & ek) > 0) {
        rA -= 8;
        return
    }
    if (ee < 10) {
        if (8 === ee)
            return r9(eu, ed, ef, ep, eC, eS, ew, ek);
        var eE = ec[rA++];
        if ((128 & eE) > 0) {
            rA -= 9;
            return
        }
        return r9(eu, ed, ef, ep, eC, eS, ew, ek, eE)
    }
    if (ee < 12) {
        var e_ = ec[rA++]
            , eT = ec[rA++];
        if ((128 & e_) > 0 || (128 & eT) > 0) {
            rA -= 10;
            return
        }
        if (ee < 11)
            return r9(eu, ed, ef, ep, eC, eS, ew, ek, e_, eT);
        var eN = ec[rA++];
        if ((128 & eN) > 0) {
            rA -= 11;
            return
        }
        return r9(eu, ed, ef, ep, eC, eS, ew, ek, e_, eT, eN)
    }
    var eM = ec[rA++]
        , eI = ec[rA++]
        , eO = ec[rA++]
        , eP = ec[rA++];
    if ((128 & eM) > 0 || (128 & eI) > 0 || (128 & eO) > 0 || (128 & eP) > 0) {
        rA -= 12;
        return
    }
    if (ee < 14) {
        if (12 === ee)
            return r9(eu, ed, ef, ep, eC, eS, ew, ek, eM, eI, eO, eP);
        var eR = ec[rA++];
        if ((128 & eR) > 0) {
            rA -= 13;
            return
        }
        return r9(eu, ed, ef, ep, eC, eS, ew, ek, eM, eI, eO, eP, eR)
    }
    var eL = ec[rA++]
        , eD = ec[rA++];
    if ((128 & eL) > 0 || (128 & eD) > 0) {
        rA -= 14;
        return
    }
    if (ee < 15)
        return r9(eu, ed, ef, ep, eC, eS, ew, ek, eM, eI, eO, eP, eL, eD);
    var eZ = ec[rA++];
    if ((128 & eZ) > 0) {
        rA -= 15;
        return
    }
    return r9(eu, ed, ef, ep, eC, eS, ew, ek, eM, eI, eO, eP, eL, eD, eZ)
}

function ou(ee) {
    if ("string" == typeof ee)
        return ee;
    if ("number" == typeof ee || "boolean" == typeof ee || "bigint" == typeof ee)
        return ee.toString();
    if (null == ee)
        return ee + "";
    throw Error("Invalid property type for record", typeof ee)
}

function ol() {
    var ee, et = ec[rA++];
    if (!(et >= 160) || !(et < 192))
        return rA--,
            ou(rK());
    if (et -= 160,
    rB >= rA)
        return ef.slice(rA - rF, (rA += et) - rF);
    if (!(0 == rB && eu < 180))
        return r0(et);
    var en = (et << 5 ^ (et > 1 ? eh.getUint16(rA) : et > 0 ? ec[rA] : 0)) & 4095
        , eo = os[en]
        , ei = rA
        , ed = rA + et - 3
        , ep = 0;
    if (eo && eo.bytes == et) {
        for (; ei < ed;) {
            if ((ee = eh.getUint32(ei)) != eo[ep++]) {
                ei = 1879048192;
                break
            }
            ei += 4
        }
        for (ed += 3; ei < ed;)
            if ((ee = ec[ei++]) != eo[ep++]) {
                ei = 1879048192;
                break
            }
        if (ei === ed)
            return rA = ei,
                eo.string;
        ed -= 3,
            ei = rA
    }
    for (eo = [],
             os[en] = eo,
             eo.bytes = et; ei < ed;)
        ee = eh.getUint32(ei),
            eo.push(ee),
            ei += 4;
    for (ed += 3; ei < ed;)
        ee = ec[ei++],
            eo.push(ee);
    var em = et < 16 ? on(et) : ot(et);
    return null != em ? eo.string = em : eo.string = r0(et)
}

const decrypt = (ee) => {
    for (var et, en, eo = atob(ee), ei = eo.length, ecc = new Uint8Array(ei), eu = 0; eu < ei; eu++) {
        var ed = eo.charCodeAt(eu);
        ecc[eu] = ed
    }
    ec = ecc;
    rA = 0;
    rB = 0;
    ed = [];
    eu = ec.length;
    rj = {
        "useRecords": false,
        "mapsAsObjects": true
    }
    // ei 是 TextDecoder
    ei = new TextDecoder("utf-8");
    eh = new DataView(ec.buffer, ec.byteOffset, ec.byteLength);
    ec.dataView = eh;
    let res = rK()
    const replacer = (key, value) => {
        if (typeof value === 'bigint') {
            return value.toString();
        }
        return value;
    };

    res = JSON.stringify(res, replacer);
    return res;
}



// console.log(generate_mid())
// console.log(generate_uuid())
// console.log(generate_device_id())
// console.log(generate_sign('5f65b00f83994987e334f97360d69557', '{"sessionTypes":"1,19"}'))
// const msg = "ggGLAYEBtTIyMDI2NDA5MTgwNzlAZ29vZmlzaAKzNDc4MTI4NzAwMDBAZ29vZmlzaAOxMzQwMjM5MTQ3MjUwMy5QTk0EAAXPAAABlYW04bIGggFlA4UBoAKjMTExA6AEAQXaADR7ImF0VXNlcnMiOltdLCJjb250ZW50VHlwZSI6MSwidGV4dCI6eyJ0ZXh0IjoiMTExIn19BwIIAQkACoupX3BsYXRmb3Jtp2FuZHJvaWSmYml6VGFn2gBBeyJzb3VyY2VJZCI6IlM6MSIsIm1lc3NhZ2VJZCI6ImYzNjkwMmVmZjQ1NDQ1YmRiMmQxYjBmZDE2OGY4MjY0In2sZGV0YWlsTm90aWNlozExMadleHRKc29u2gBLeyJxdWlja1JlcGx5IjoiMSIsIm1lc3NhZ2VJZCI6ImYzNjkwMmVmZjQ1NDQ1YmRiMmQxYjBmZDE2OGY4MjY0IiwidGFnIjoidSJ9r3JlbWluZGVyQ29udGVudKMxMTGucmVtaW5kZXJOb3RpY2W15Y+R5p2l5LiA5p2h5paw5raI5oGvrXJlbWluZGVyVGl0bGWmc2hh5L+uq3JlbWluZGVyVXJs2gCbZmxlYW1hcmtldDovL21lc3NhZ2VfY2hhdD9pdGVtSWQ9ODk3NzQyNzQ4MDExJnBlZXJVc2VySWQ9MjIwMjY0MDkxODA3OSZwZWVyVXNlck5pY2s9dCoqKjEmc2lkPTQ3ODEyODcwMDAwJm1lc3NhZ2VJZD1mMzY5MDJlZmY0NTQ0NWJkYjJkMWIwZmQxNjhmODI2NCZhZHY9bm+sc2VuZGVyVXNlcklkrTIyMDI2NDA5MTgwNzmuc2VuZGVyVXNlclR5cGWhMKtzZXNzaW9uVHlwZaExDAEDgahuZWVkUHVzaKR0cnVl";
// res = decrypt(msg);
// console.log(res);