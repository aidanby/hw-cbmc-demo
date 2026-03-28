// CRC-8/SMBUS serial processor: shifts in one bit per clock,
// computing CRC with polynomial 0x07 (x^8 + x^2 + x + 1).
// Feedback XOR is applied when the outgoing bit (crc[7]) is 1.
// The CRC register is not computing the correct checksum.
module crc8(input clk, input reset, input din, output reg [7:0] crc);
  initial crc = 8'h00;

  always @(posedge clk) begin
    if (reset) begin
      crc <= 8'hFF;  // should be 8'h00
    end else begin
      if (crc[7] ^ din)
        crc <= {crc[6:0], 1'b0} ^ 8'h83;  // should be ^ 8'h07
      else
        crc <= {crc[6:0], 1'b0};
    end
  end

  p_reset:    assert property (@(posedge clk) reset |=> crc == 8'h00);
  p_feedback: assert property (@(posedge clk) !reset && (crc[7] ^ din) |=> crc == (($past(crc) << 1) ^ 8'h07));
  p_shift:    assert property (@(posedge clk) !reset && !(crc[7] ^ din) |=> crc == ($past(crc) << 1));
endmodule
