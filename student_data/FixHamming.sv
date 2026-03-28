// Hamming(7,4) encoder: encodes 4 data bits into 7-bit codeword with 3 parity bits.
// Data bits: d0(bit1), d1(bit2), d2(bit3), d3(bit4) -- 1-indexed positions.
// Parity coverage: p1 covers positions {1,3,5,7} = d0,d1,d3
//                  p2 covers positions {2,3,6,7} = d0,d2,d3
//                  p4 covers positions {4,5,6,7} = d1,d2,d3
// The encoder is computing incorrect parity bits.
module hamming74(input [3:0] d, output [6:0] cw);
  wire p1, p2, p4;
  assign p1 = d[0] ^ d[2] ^ d[3];  // should be d[0]^d[1]^d[3]
  assign p2 = d[1] ^ d[2] ^ d[3];  // should be d[0]^d[2]^d[3]
  assign p4 = d[0] ^ d[1] ^ d[2];  // should be d[1]^d[2]^d[3]
  assign cw = {d[3], d[2], d[1], d[0], p4, p2, p1};

  p_p1: assert final (p1 == (d[0] ^ d[1] ^ d[3]));
  p_p2: assert final (p2 == (d[0] ^ d[2] ^ d[3]));
  p_p4: assert final (p4 == (d[1] ^ d[2] ^ d[3]));
endmodule
